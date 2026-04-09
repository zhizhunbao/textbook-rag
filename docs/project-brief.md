# Ottawa EcDev GenAI Research Tool – Consolidated Brief

---

## 1. Purpose & Scope
- Build a GenAI research assistant for Economic Development (EcDev) analysts that answers natural-language questions, generates narrative updates, charts, and speaking notes directly from an updatable document corpus (primarily PDFs) without redeploying the system.
- Phase 1 focuses on Economic Development (ED) Update reports hosted on ottawa.ca (Q1 2022 – Q4 2025), with EcDev supplying the PDF library as needed.
  - Example report: [Economic Development Update – Q4 2024](https://documents.ottawa.ca/sites/default/files/economic_update_q4_2024_en.pdf)
  - All PDFs available at: [Economic development update | City of Ottawa](https://ottawa.ca/en/planning-development-and-construction/housing-and-development-reports/local-economic-development-information/economic-development-update)
  - Note: Gap in publication due to COVID (Q3 2019 – Q3 2021), focus on Q1 2022 – Q4 2025
- Phase 2 expands to external sources via APIs (e.g., Statistics Canada) and targeted PDF scraping (e.g., [Ottawa Real Estate Board Market Update example](https://www.oreb.ca/wp-content/uploads/2025/08/OREB_MarketUpdate_HLP_July25.pdf)).

## 2. Core User Needs
- Ask open-ended questions and receive sourced reports/visuals tied to Ottawa’s economy.
- Produce periodic narrative summaries, tables, and graphs for reports or presentations.
- Summarize lengthy documents or web content with ready-to-use speaking notes.
- Provide credible outputs with trustability metrics (hallucination measure, validity) and cite underlying sources for every response.

## 3. Data Inputs & Stakeholders
- **Primary City sources:** ED Update PDFs on ottawa.ca, ED site content (with refreshed fall release), City Newsroom (Business/Economy/Innovation), Ottawa Business Journal.
- **External partners & data providers:**
  - **Chambers & Organizations:** Ottawa Board of Trade, Regroupement des Gens d'Affaires de la Capitale Nationale (Francophone Chamber of Commerce), Invest Ottawa (Lead Economic Development Agency), YOW (Airport)
  - **Tourism & Creative:** Ottawa Tourism, Ottawa Film Office, Ottawa Music Industry Coalition, Ottawa Festivals
  - **Districts:** Business Improvement Areas, ByWard Market District Authority
  - **Research Organizations:** Statistics Canada, Conference Board of Canada, Canadian Urban Institute
  - **Real Estate:** Ottawa Real Estate Board, Canada Mortgage and Housing Corporation (CMHC)
  - **Research Firms:** Colliers, Cushman & Wakefield, Marcus & Millichap, CBRE
- **Collaboration:** Keep SMEs (Js, Eric) looped in for business context; development treated as greenfield but aligned with City guidance.

## 4. Trustability Targets & Evaluation
- Every answer must include source tracking and a trustability indicator.
- Initial metrics for held-out question sets:
  - Accuracy ≥ 75%
  - Faithfulness ≥ 90%
  - Context recall ≥ 85%
- Further research required on hallucination avoidance and evaluation libraries (students to propose options; SMEs to provide recommendations).

## 5. Delivery Phases & Timelines
- **Phase 1 (Sep–Dec 2025):** RAG-based prototype over ED Update PDFs, enabling Q&A, summaries, visual generation, and agentic workflows within the City environment.
- **Phase 2 (Jan–Apr 2026):** Integrate at least one external data source via API (e.g., StatsCan APIs for key economic indicators), plus PDF scraping pipelines (e.g., OREB market updates); expand analytics outputs.

## 6. Technical & Security Guidance
- Data is public, but adhere to City's preferred Azure-based stack and document all libraries.
- All platform components must be Azure-native services to ensure enterprise security, compliance, and support.
- **Required Azure Platform Components:**
  - **LLM & Embeddings:** Azure OpenAI Service (GPT-4o, GPT-4 Turbo for generation; text-embedding-ada-002 for embeddings)
  - **Vector Storage:** Azure AI Search (hybrid semantic + keyword search with vector indexing)
  - **Document Storage:** Azure Blob Storage (secure PDF storage with managed access)
  - **Orchestration:** Microsoft Semantic Kernel with FastAPI backend orchestrator
  - **Authentication:** Azure Entra ID (single sign-on and role-based access control)
  - **Secret Management:** Azure Key Vault (API keys, connection strings, certificates)
  - **Monitoring:** Azure Application Insights with OpenTelemetry instrumentation
  - **Frontend:** React TypeScript application hosted on Azure Static Web Apps or Azure App Service
  - **Analytics:** Python libraries (NumPy, pandas, Matplotlib/Seaborn) running on Azure Container Apps
  - **Evaluations:** Azure-compatible evaluation frameworks with metrics stored in Azure Monitor
- **Development Environment:** Students use Azure subscriptions (student accounts or institutional environments) for all development and testing.
- **Testing/Production Environment:** Deploy to Azure Container Apps or Azure App Service with City IT team collaboration for enterprise integration and security compliance.

## 7. Outstanding Actions
- Draft detailed plan aligning solution architecture with trustability metrics and agentic RAG exploration using Azure-native services.
- Confirm Azure-compatible evaluation library stack once City SMEs share recommendations; supplement with Azure Monitor integration.
- Continue documenting assumptions, risk areas, and Azure service usage for SME review.
- Provide list of Azure-compatible evaluation-metric libraries and monitoring solutions.
- Students to draft implementation plan using exclusively Azure services, aligning with enterprise security and compliance requirements.

---

## Additional Notes
- City cannot share existing project code or OpenAI usage patterns.
- All technology components must use Azure services to ensure enterprise compliance, security, and long-term support.
- Deliver tangible Azure-based solution for City SMEs to review and adopt within municipal IT infrastructure.
- Goal: address focus areas above and extend with Agentic RAG capabilities using Microsoft Semantic Kernel and Azure AI services.
- Ensure all API integrations, data storage, and processing align with Azure enterprise security standards and City IT policies.

