#!/bin/bash
# Demo queries script - runs bean-query and outputs markdown results.
# Usage: ./scripts/run-demo-queries.sh [beancount_file] [output_file]

BEANCOUNT_FILE="${1:-main.beancount}"
OUTPUT_FILE="${2:-/dev/stdout}"

if command -v uv &> /dev/null; then
    BEAN_QUERY="uv run bean-query"
else
    BEAN_QUERY="bean-query"
fi

run_query() {
    local title="$1"
    local description="$2"
    local query="$3"

    echo ""
    echo "### $title"
    echo ""
    echo "$description"
    echo ""

    result=$($BEAN_QUERY "$BEANCOUNT_FILE" "$query" 2>/dev/null)
    exit_code=$?

    if [[ $exit_code -ne 0 ]] || [[ -z "${result// }" ]]; then
        echo "_No data available_"
    else
        echo '```'
        echo "$result"
        echo '```'
    fi
}

{
    echo "## Spending Insights"
    echo ""
    echo "These queries provide a summary of spending patterns from the imported transactions."

    run_query "Coffee Spending by Month" \
        "Track your caffeine habit across months." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Coffee'
         GROUP BY year, month
         ORDER BY year, month"

    run_query "Transport & Commute by Month" \
        "Monthly spending on public transport and fuel." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Transport'
         GROUP BY year, month
         ORDER BY year, month"

    run_query "Subscriptions by Month" \
        "Recurring subscription costs (streaming, music, internet, dev tools)." \
        "SELECT year, month, account, sum(position) AS total
         WHERE account ~ 'Expenses:Subscriptions'
         GROUP BY year, month, account
         ORDER BY year, month, account"

    run_query "Quarterly Spending by Category" \
        "High-level view of where money goes each quarter." \
        "SELECT year, quarter(date) AS quarter, root(account, 2) AS category, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY year, quarter(date), root(account, 2)
         ORDER BY year, quarter(date), total DESC"

    run_query "Top Spending Categories" \
        "Overall spending breakdown by category." \
        "SELECT account, count(position) AS transactions, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY account
         ORDER BY total DESC
         LIMIT 10"

    run_query "Monthly Expense Totals" \
        "Total expenses per month." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses'
         GROUP BY year, month
         ORDER BY year, month"

    run_query "Groceries by Month" \
        "Monthly grocery spending." \
        "SELECT year, month, sum(position) AS total
         WHERE account ~ 'Expenses:Groceries'
         GROUP BY year, month
         ORDER BY year, month"

    echo ""
    echo "## Loan Insights"
    echo ""
    echo "Track your mortgage payments and see how extra payments save you money on interest."

    run_query "How Much Do I Save by Repaying Loan?" \
        "Extra principal payments reduce your loan faster and save on future interest. This shows your extra payments that go directly to reducing the principal." \
        "SELECT year, month, narration, sum(position) AS extra_payment
         WHERE account ~ 'Liabilities:Loan' AND narration ~ 'Extra'
         GROUP BY year, month, narration
         ORDER BY year, month"

    run_query "Interest Paid on Loan by Month" \
        "Monthly interest payments on your mortgage. Lower interest over time means your extra payments are working." \
        "SELECT year, month, sum(position) AS interest_paid
         WHERE account ~ 'Expenses:Interest'
         GROUP BY year, month
         ORDER BY year, month"

    run_query "Loan Principal Paid by Month" \
        "How much of your payment goes to actually paying down the loan, not interest." \
        "SELECT year, month, sum(position) AS principal_paid
         WHERE account ~ 'Liabilities:Loan' AND narration ~ 'Mortgage Payment|Extra Mortgage Payment'
         GROUP BY year, month
         ORDER BY year, month"

    run_query "Loan Payment Summary" \
        "Overview of total principal paid vs total interest paid." \
        "SELECT account, sum(position) AS total
         WHERE (account ~ 'Liabilities:Loan' AND narration ~ 'Mortgage Payment|Extra Mortgage Payment')
            OR account ~ 'Expenses:Interest'
         GROUP BY account
         ORDER BY account"

    echo ""
    echo "---"
    echo "_Queries generated using \`bean-query\` from Beancount_"
} > "$OUTPUT_FILE"

echo "Demo queries completed. Output written to: $OUTPUT_FILE"
