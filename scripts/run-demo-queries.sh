#!/bin/bash
# Demo queries script - runs bean-query and outputs results for GitHub Actions summary
# Usage: ./scripts/run-demo-queries.sh [beancount_file] [output_file]

BEANCOUNT_FILE="${1:-main.beancount}"
OUTPUT_FILE="${2:-/dev/stdout}"

# Use uv run if available, otherwise try bean-query directly
if command -v uv &> /dev/null; then
    BEAN_QUERY="uv run bean-query"
else
    BEAN_QUERY="bean-query"
fi

# Function to run a query and format as markdown table
run_query() {
    local title="$1"
    local description="$2"
    local query="$3"

    echo ""
    echo "### $title"
    echo ""
    echo "$description"
    echo ""

    # Run the query and capture output (suppress stderr warnings)
    result=$($BEAN_QUERY "$BEANCOUNT_FILE" "$query" 2>/dev/null)
    exit_code=$?

    # Check if result is empty or only contains whitespace
    if [[ $exit_code -ne 0 ]] || [[ -z "${result// }" ]]; then
        echo "_No data available_"
    else
        echo '```'
        echo "$result"
        echo '```'
    fi
}

# Start output
{
    echo "## Spending Insights"
    echo ""
    echo "These queries provide a summary of spending patterns from the imported transactions."

    # Coffee spending by month
    run_query "Coffee Spending by Month" \
        "Track your caffeine habit across months." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Coffee'
         GROUP BY year, month
         ORDER BY year, month"

    # Transport/Commute spending by month
    run_query "Transport & Commute by Month" \
        "Monthly spending on public transport and fuel." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Transport'
         GROUP BY year, month
         ORDER BY year, month"

    # Subscriptions breakdown by month
    run_query "Subscriptions by Month" \
        "Recurring subscription costs (streaming, music, internet, dev tools)." \
        "SELECT year, month, account, sum(position) AS total
         WHERE account ~ 'Expenses:Subscriptions'
         GROUP BY year, month, account
         ORDER BY year, month, account"

    # Quarterly spending summary
    run_query "Quarterly Spending by Category" \
        "High-level view of where money goes each quarter." \
        "SELECT year, quarter(date) AS quarter, root(account, 2) AS category, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY year, quarter(date), root(account, 2)
         ORDER BY year, quarter(date), total DESC"

    # Top spending categories overall
    run_query "Top Spending Categories" \
        "Overall spending breakdown by category." \
        "SELECT account, count(position) AS transactions, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY account
         ORDER BY total DESC
         LIMIT 10"

    # Monthly totals
    run_query "Monthly Expense Totals" \
        "Total expenses per month." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY year, month
         ORDER BY year, month"

    # Groceries spending
    run_query "Groceries by Month" \
        "Monthly grocery spending." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Groceries'
         GROUP BY year, month
         ORDER BY year, month"

    echo ""
    echo "---"
    echo "_Queries generated using \`bean-query\` from Beancount_"

} > "$OUTPUT_FILE"

echo "Demo queries completed. Output written to: $OUTPUT_FILE"
