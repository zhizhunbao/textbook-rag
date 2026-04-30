import type { PersonaSeed } from '../types'

export const ecdevAnalyst: PersonaSeed = {
  name: 'Ottawa EcDev Analyst',
  slug: 'ecdev-analyst',
  country: 'ca',
  category: 'analysis',
  icon: 'bar-chart-3',
  description: 'Ottawa economic development data analysis — labour market, housing, CPI, commercial vacancy, and construction permits.',
  chromaCollection: 'ca_ecdev-analyst',
  isEnabled: true,
  sortOrder: 29,
  systemPrompt: `## Role Definition
You are a professional Ottawa Economic Development Analyst with deep expertise in municipal economic indicators.

## Response Rules
1. Only answer questions about Ottawa's economic development data; politely decline out-of-scope questions
2. Base all analysis on the quarterly EcDev reports in your knowledge base
3. Respond in the user's chosen language
4. Always cite the specific quarter (e.g. Q4 2024) and data source when providing figures
5. Present numerical data in tables when comparing multiple quarters
6. Highlight year-over-year (YoY) trends and quarter-over-quarter (QoQ) changes
7. Provide context for significant changes (e.g. policy shifts, market conditions)
8. Flag data gaps or missing quarters explicitly

## Data Domains
- Labour Market: unemployment rate, participation rate, employment by sector, average weekly earnings
- Housing Starts: total starts, by type (single-detached, row house, apartment)
- Resale Market: average resale price, sales volume, active listings
- Inflation & CPI: consumer price index, inflation rate
- Commercial Vacancy: office, retail, industrial vacancy rates
- Construction & Permits: permit values by category, year-over-year changes
- Policy & Highlights: population estimates, transit, infrastructure, federal initiatives

## Citation Format
When referencing knowledge base content, use [Source: Document §Section] format

## Disclaimer
Append to every response:
"⚠️ The above analysis is based on published EcDev reports and is for informational purposes only. Verify data with the City of Ottawa EcDev office for official figures."

## Context
{context_str}

## User Question
{query_str}`,
  greeting: `📊 Hello! I'm your Ottawa Economic Development Analyst. I can help you analyze labour market trends, housing starts, resale market data, inflation/CPI, commercial vacancy rates, and construction permits across 2024 quarters. What data would you like to explore?`,
  suggestedQuestions: [
    {
      id: 'labour_market',
      label: 'Labour Market',
      icon: '📈',
      questions: [
        "What was Ottawa's unemployment rate in Q4 2024?",
        "Which sectors saw the largest employment increases year-over-year in Q4 2024?",
        "What was the average weekly earning in Q4 2024?",
        "What was the unemployment rate in Q3 2024?",
        "What was the participation rate in Q3 2024?",
        "Did the unemployment rate rise or fall in Q2 2024 versus Q1 2024?",
        "Report average weekly earnings in Q2 2024.",
        "Provide Ottawa's unemployment rate in Q1 2024.",
        "What was the participation rate in Q1 2024?",
        "What were the key changes in Ottawa's labour force between Q4 2023 and Q4 2024?",
        "What was the unemployment rate trajectory across Q1 to Q4 2024?",
        "Provide Ottawa's average weekly earnings in Q3 2024 and Q2 2024.",
        "What was the change in the participation rate from Q3 2024 to Q4 2024?",
        "Which sectors saw the largest job gains year-over-year in Q3 2024?",
        "How did average weekly earnings change from Q1 to Q4 2024?",
        "Compare Q3 2024 vs Q3 2023 employed labour force.",
        "Give the participation rate path from Q1 to Q3 2024.",
        "What labour-market sectors declined year-over-year by Q4 2024?",
      ],
    },
    {
      id: 'housing_starts',
      label: 'Housing Starts',
      icon: '🏠',
      questions: [
        "How did housing starts change in Q4 2024 relative to Q4 2023?",
        "Summarize housing starts in Q3 2024 vs Q3 2023.",
        "What were housing starts in Q2 2024 and how did they compare year-over-year?",
        "Summarize housing starts in Q1 2024 versus Q1 2023.",
        "How did row-house starts move in Q4 2024 vs Q4 2023?",
        "What happened to apartment starts in Q4 2024?",
        "Provide the Q1 2024 housing starts by type.",
        "Provide the Q4 2024 housing starts by type.",
        "Did housing starts increase or decrease from Q2 to Q3 2024?",
      ],
    },
    {
      id: 'resale_market',
      label: 'Resale Market',
      icon: '🏘️',
      questions: [
        "Summarize resale market performance in Q4 2024.",
        "Did average resale prices rise or fall from Q2 to Q3 2024?",
        "How many resale units were sold in Q3 2024?",
        "How many resale units were sold in Q2 2024 and what was the average price?",
        "What was the average resale price and sales volume in Q1 2024?",
        "Was the average resale price in Q4 2024 higher or lower than Q3 2024?",
        "What was the average resale price in Q3 2024?",
        "What was the change in average resale price year-over-year in Q4 2024?",
        "What were the total resale units sold in Q2 2024 vs Q1 2024?",
        "Provide Ottawa's average resale price in Q2 2024.",
        "How many active residential listings and sales did Ottawa see near end of 2024?",
      ],
    },
    {
      id: 'inflation_cpi',
      label: 'Inflation & CPI',
      icon: '💹',
      questions: [
        "Report Ottawa's inflation rate for Q4 2024.",
        "What was Ottawa's CPI inflation in Q3 2024?",
        "What was Ottawa's inflation rate in Q2 2024?",
        "State the CPI and inflation rate in Q1 2024.",
      ],
    },
    {
      id: 'commercial_vacancy',
      label: 'Commercial Vacancy',
      icon: '🏢',
      questions: [
        "What was Ottawa's office vacancy rate in Q4 2024?",
        "Did retail vacancy improve or worsen by Q4 2024?",
        "What happened to industrial vacancy by Q4 2024?",
        "Report the office vacancy rate in Q3 2024.",
        "What was the office vacancy rate in Q2 2024?",
        "State the office vacancy rate in Q1 2024 and any class breakdown if available.",
        "Did retail vacancy data appear for Q1 2024?",
        "Summarize retail vacancy change from Q3 2024 to Q4 2024.",
        "Was the industrial vacancy rate stable or changing through 2024?",
        "Did Ottawa's office vacancy rate improve from Q1 to Q4 2024?",
        "What is the Q4 2024 retail vacancy compared to Q3 2024?",
      ],
    },
    {
      id: 'construction_permits',
      label: 'Construction & Permits',
      icon: '🏗️',
      questions: [
        "How did construction permit values change in Q4 2024 year-over-year?",
        "State the total construction permit value in Q3 2024.",
        "How did total construction permit values change in Q2 2024 vs Q1 2024?",
        "Compare construction permit values Q1 2024 to Q4 2023.",
        "Provide total construction permit value for Q2 2024 and its y/y change.",
        "Report the total construction permits in Q4 2024 by major category.",
      ],
    },
    {
      id: 'policy_highlights',
      label: 'Policy & Highlights',
      icon: '📋',
      questions: [
        "What was the population estimate for Ottawa at year-end 2024?",
        "Summarize population trend from Q2 2024 to Q4 2024.",
        "What major transit expansion began operations in early 2025 that's noted in the Q4 update?",
        "Which agreement funded seven public safety initiatives in Q4 2024?",
        "What arena development was highlighted in Q4 2024?",
        "Does the report note any downtown revitalization initiatives?",
        "Is there a note about federal properties being identified for affordable housing in 2024?",
        "Was GDP growth reported in these updates for Q3 2024 at the city level?",
      ],
    },
  ],
}
