"""Case content for the introductory Diagnosing Dollars experience."""

COMPANY_NAME = "Gem City Outfitters"
COMPANY_DESCRIPTION = (
    "A regional outdoor retailer with a 90-day operating cycle. Management is "
    "requesting an expanded line of credit to open a second location."
)

CATEGORIES = (
    "Current assets",
    "Long-term investments",
    "Property, plant, and equipment",
    "Intangible assets",
    "Current liabilities",
    "Long-term liabilities",
    "Shareholders' Equity",
)

ACCOUNTS = (
    {
        "name": "Cash",
        "amount": 90_000,
        "category": "Current assets",
        "why": "Cash is already liquid and is reported first among current assets.",
    },
    {
        "name": "Accounts receivable",
        "amount": 160_000,
        "category": "Current assets",
        "why": "Customer balances are expected to be collected during the operating cycle.",
    },
    {
        "name": "Inventory",
        "amount": 300_000,
        "category": "Current assets",
        "why": "Inventory is expected to be sold during the operating cycle.",
    },
    {
        "name": "Prepaid insurance",
        "amount": 30_000,
        "category": "Current assets",
        "why": "The insurance benefit will be used within the next year.",
    },
    {
        "name": "Corporate bonds held for three years",
        "amount": 120_000,
        "category": "Long-term investments",
        "why": "The bonds are investments that management plans to hold longer than one year.",
    },
    {
        "name": "Land held for a store planned in four years",
        "amount": 180_000,
        "category": "Long-term investments",
        "why": "The land is not currently used in operations, so it is a long-term investment.",
    },
    {
        "name": "Store equipment",
        "amount": 480_000,
        "category": "Property, plant, and equipment",
        "why": "The equipment is a long-lived asset currently used in operations.",
    },
    {
        "name": "Accumulated depreciation—store equipment",
        "amount": -120_000,
        "category": "Property, plant, and equipment",
        "why": "Accumulated depreciation is reported with the related equipment and reduces its book value.",
    },
    {
        "name": "Trademark",
        "amount": 80_000,
        "category": "Intangible assets",
        "why": "A trademark provides value but has no physical substance.",
    },
    {
        "name": "Accounts payable",
        "amount": 180_000,
        "category": "Current liabilities",
        "why": "Supplier balances are expected to be paid during the operating cycle.",
    },
    {
        "name": "Salaries and wages payable",
        "amount": 40_000,
        "category": "Current liabilities",
        "why": "The unpaid employee obligation is due in the near term.",
    },
    {
        "name": "Note payable due in eight months",
        "amount": 100_000,
        "category": "Current liabilities",
        "why": "The note is current because its maturity date is within one year.",
    },
    {
        "name": "Bonds payable due in 2032",
        "amount": 400_000,
        "category": "Long-term liabilities",
        "why": "The bonds mature after one year.",
    },
    {
        "name": "Common stock",
        "amount": 250_000,
        "category": "Shareholders' Equity",
        "why": "Common stock is a component of shareholders' equity and reports assets invested by shareholders.",
    },
    {
        "name": "Retained earnings",
        "amount": 350_000,
        "category": "Shareholders' Equity",
        "why": "Retained earnings is a component of shareholders' equity and represents income retained for use in the business.",
    },
)

LIQUIDITY_ORDER = (
    "Cash",
    "Accounts receivable",
    "Inventory",
    "Prepaid insurance",
)

CONTEXT_QUESTIONS = (
    {
        "id": "office_land",
        "prompt": "If the company instead used the land for its current corporate office, where would the land be classified?",
        "options": (
            "Current assets",
            "Long-term investments",
            "Property, plant, and equipment",
            "Intangible assets",
        ),
        "correct": "Property, plant, and equipment",
        "why": "Classification depends on use. Land currently used in operations is property, plant, and equipment.",
    },
    {
        "id": "five_year_cd",
        "prompt": "How should a certificate of deposit maturing in five years and reserved for the future store be classified?",
        "options": (
            "Current assets",
            "Long-term investments",
            "Property, plant, and equipment",
            "Intangible assets",
        ),
        "correct": "Long-term investments",
        "why": "The certificate is held beyond one year for a long-term purpose.",
    },
    {
        "id": "note_due",
        "prompt": "What fact makes the eight-month note payable a current liability?",
        "options": (
            "It is called a note",
            "It has an interest rate",
            "Its maturity falls within one year",
            "It was issued by a retailer",
        ),
        "correct": "Its maturity falls within one year",
        "why": "Notes can be current or long-term. The maturity date determines the classification here.",
    },
)

CURRENT_FINANCIALS = {
    "current_assets": 580_000,
    "current_liabilities": 320_000,
    "total_liabilities": 720_000,
    "total_assets": 1_320_000,
    "total_equity": 600_000,
}

PRIOR_FINANCIALS = {
    "current_assets": 520_000,
    "current_liabilities": 260_000,
    "total_liabilities": 600_000,
    "total_assets": 1_200_000,
    "total_equity": 600_000,
}

BENCHMARKS = {
    "Average of all peers": {
        "working_capital": None,
        "current_ratio": 1.70,
        "debt_to_assets": 48.0,
        "debt_to_equity": 92.0,
    },
    "River City Gear (competitor)": {
        "working_capital": 310_000,
        "current_ratio": 2.10,
        "debt_to_assets": 45.0,
        "debt_to_equity": 82.0,
    },
}

ANALYSIS_QUESTIONS = (
    {
        "id": "working_capital_story",
        "prompt": "Working capital stayed at $260,000, but the current ratio declined. What best explains this?",
        "options": (
            "Current liabilities grew faster, proportionally, than current assets",
            "The company has no current assets",
            "Working capital and the current ratio always move in opposite directions",
            "Long-term bonds were converted to common stock",
        ),
        "correct": "Current liabilities grew faster, proportionally, than current assets",
        "why": "Both amounts rose by $60,000, but that increase was much larger relative to the smaller beginning current-liability balance.",
    },
    {
        "id": "composition",
        "prompt": "Which fact deserves the most attention when judging short-term liquidity?",
        "options": (
            "More than half of current assets are inventory",
            "The company owns a trademark",
            "The company reports common stock",
            "The bonds payable have a stated maturity date",
        ),
        "correct": "More than half of current assets are inventory",
        "why": "Inventory may take longer to sell and convert to cash than cash or receivables.",
    },
    {
        "id": "solvency",
        "prompt": "What is the strongest conclusion from the debt ratios?",
        "options": (
            "Long-term risk has increased and is above both comparison points",
            "The company has eliminated all creditor financing",
            "Solvency is stronger because every debt ratio increased",
            "Debt ratios measure only short-term liquidity",
        ),
        "correct": "Long-term risk has increased and is above both comparison points",
        "why": "Higher debt-to-assets and debt-to-equity ratios indicate greater reliance on creditor financing and greater risk.",
    },
)

COMPARISON_QUESTIONS = (
    {
        "id": "prior_type",
        "label": "Current year compared with Gem City Outfitters last year",
        "correct": "Intracompany comparison",
        "why": "Comparing the same company across different years is an intracompany comparison.",
    },
    {
        "id": "industry_type",
        "label": "Current year compared with the average of all peers",
        "correct": "Industry-average comparison",
        "why": "Comparing one company with the average results of its peer group is an industry-average comparison.",
    },
    {
        "id": "competitor_type",
        "label": "Current year compared with River City Gear",
        "correct": "Intercompany comparison",
        "why": "Comparing one company with a specific competitor is an intercompany comparison.",
    },
)

COMPARISON_OPTIONS = (
    "Intracompany comparison",
    "Industry-average comparison",
    "Intercompany comparison",
)

DIAGNOSIS_QUESTIONS = (
    {
        "id": "liquidity_diagnosis",
        "prompt": "What is the best short-term liquidity diagnosis?",
        "options": (
            "Immediate emergency: the company cannot cover any current obligations",
            "Generally adequate, but monitor the decline and inventory concentration",
            "Perfect health: no additional analysis is needed",
        ),
        "correct": "Generally adequate, but monitor the decline and inventory concentration",
        "why": "Working capital is positive and the current ratio exceeds the peer average, but the trend and asset composition create caution.",
    },
    {
        "id": "solvency_diagnosis",
        "prompt": "What is the best long-term solvency diagnosis?",
        "options": (
            "Lower risk because creditor financing decreased",
            "Unchanged risk because total equity did not change",
            "Higher risk because debt financing increased relative to assets and equity",
        ),
        "correct": "Higher risk because debt financing increased relative to assets and equity",
        "why": "Both debt ratios increased and are higher than the peer average and competitor benchmarks.",
    },
    {
        "id": "lender_recommendation",
        "prompt": "As the lender, which recommendation is best supported?",
        "options": (
            "Approve automatically with no follow-up",
            "Reject solely because inventory exists",
            "Consider approval with conditions and continued monitoring",
        ),
        "correct": "Consider approval with conditions and continued monitoring",
        "why": "The evidence is mixed: near-term coverage is adequate, while the trend, inventory concentration, and debt burden warrant safeguards.",
    },
)

EVIDENCE_OPTIONS = (
    "Positive working capital of $260,000",
    "Current ratio above the peer average but below last year",
    "More than half of current assets held in inventory",
    "Debt ratios above last year, the industry, and the competitor",
    "The trademark guarantees that current liabilities will be paid",
    "The existence of common stock eliminates solvency risk",
)

CORRECT_EVIDENCE = frozenset(EVIDENCE_OPTIONS[:4])
