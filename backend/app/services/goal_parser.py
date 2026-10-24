import re
import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.models.goal import GoalParseResponse, MilestoneParseItem
from backend.app.services.ai_provider import ai_provider

logger = logging.getLogger("northstar.goal_parser")

def _detect_domain(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ["student", "attendance", "course", "grade", "school", "university", "curriculum", "ferpa"]):
        return "Education & Academic Management"
    elif any(k in text_lower for k in ["paper", "literature", "citation", "research", "experiment", "dataset", "scientific", "study", "findings"]):
        return "Scientific Research & Analysis"
    elif any(k in text_lower for k in ["patient", "clinical", "hospital", "hipaa", "medical", "doctor", "health", "triage"]):
        return "Healthcare Administration & Clinical Systems"
    elif any(k in text_lower for k in ["portfolio", "trading", "transaction", "rebalance", "bank", "financial", "ledger", "stock", "sec "]):
        return "Financial Systems & FinTech"
    elif any(k in text_lower for k in ["jira", "linear", "scrum", "kanban", "sprint", "roadmap", "project management"]):
        return "Project Management & Operations"
    elif any(k in text_lower for k in ["python", "postgresql", "react", "api", "database", "backend", "frontend", "microservices", "docker", "code", "software", "system", "app"]):
        return "Software Engineering & Architecture"
    return "General Autonomous Mission"

def parse_goal_heuristic(text: str) -> GoalParseResponse:
    domain = _detect_domain(text)
    clean_text = text.strip()
    first_sentence = re.split(r'[.!?\n]', clean_text)[0].strip()
    
    # Synthesize Title
    if len(first_sentence) < 60 and len(first_sentence) > 5:
        title = first_sentence
    else:
        words = first_sentence.split()
        title = " ".join(words[:7]) + ("..." if len(words) > 7 else "")
    # Clean leading verbs for a clean title
    for prefix in ["build a ", "build ", "create a ", "create ", "implement a ", "implement ", "develop a ", "develop "]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):].capitalize()
            break

    # Extract technologies or explicit requirements
    tech_matches = re.findall(r'\b(python|postgresql|postgres|mysql|sqlite|fastapi|django|flask|react|vue|node|nextjs|docker|kubernetes|aws|azure|jwt|oauth|graphql|rest|typescript)\b', clean_text, re.IGNORECASE)
    tech_set = list(dict.fromkeys([t.title() for t in tech_matches]))

    # Domain-specific constraints, criteria, anti-goals, milestones, and questions
    invariants: List[str] = []
    criteria: List[str] = []
    anti_goals: List[str] = []
    milestones: List[MilestoneParseItem] = []
    missing_info: List[str] = []
    clarifying_questions: List[str] = []

    if domain == "Education & Academic Management":
        invariants = [
            "Must ensure absolute privacy of student records (FERPA/GDPR compliance)",
            f"Must utilize specified tech stack: {', '.join(tech_set) if tech_set else 'Python and verified relational database'}",
            "Must maintain immutable audit trail for all attendance status changes",
            "Zero tolerance for fabricated, simulated, or bulk-unverified attendance records"
        ]
        criteria = [
            "Student roster and enrollment data persistence verified in database",
            "Attendance tracking API supports Present, Absent, Excused, and Tardy states",
            "Reporting module generates accurate daily, weekly, and aggregate attendance summaries",
            "Role-based access control verified (Instructor vs Student vs Admin)"
        ]
        anti_goals = [
            "Do not expose student personally identifiable information (PII) in logs or unauthenticated APIs",
            "Do not allow retroactive attendance modifications without authorized instructor reason",
            "Do not mock attendance verification tests to force artificial passes"
        ]
        milestones = [
            MilestoneParseItem(
                order_index=1,
                title="M-1: Database Schema & Student Data Model",
                description="Design and apply relational schemas for students, classes, and attendance logs with integrity constraints.",
                dependencies=[]
            ),
            MilestoneParseItem(
                order_index=2,
                title="M-2: Core Attendance Ingestion & Verification API",
                description="Implement endpoints for taking attendance, validating timestamps, and enforcing role authorization.",
                dependencies=["M-1"]
            ),
            MilestoneParseItem(
                order_index=3,
                title="M-3: Reporting Engine & Export Capabilities",
                description="Build statistical aggregation pipelines for absenteeism rates, report generation, and CSV/PDF export.",
                dependencies=["M-2"]
            ),
            MilestoneParseItem(
                order_index=4,
                title="M-4: Security Audit, PII Protection & Acceptance Testing",
                description="Execute end-to-end security audits, verify FERPA compliance guardrails, and test against edge cases.",
                dependencies=["M-3"]
            )
        ]
        missing_info = [
            "Specific authentication mechanism (e.g. Single Sign-On, OAuth2, or JWT credentials)",
            "Attendance correction workflow policy (e.g. allowed window for retroactive adjustments)"
        ]
        clarifying_questions = [
            "Would you like SSO integration (Google Workspace / Microsoft 365) or standard username/password authentication?",
            "What is the required data retention policy for archived academic year attendance records?"
        ]

    elif domain == "Scientific Research & Analysis":
        invariants = [
            "Must cite verified primary academic sources with DOI or arXiv references",
            "Zero tolerance for hallucinated or fabricated citations or research conclusions",
            "Must document methodology and reproducible search criteria",
            "Synthesis must clearly distinguish empirical findings from author hypotheses"
        ]
        criteria = [
            "Literature review covers key recent papers in the specified domain",
            "Structured comparative matrix generated evaluating architectures, benchmarks, and tradeoffs",
            "Markdown report compiled with verified bibtex/citations",
            "Fact-checking pass executed against original source PDFs"
        ]
        anti_goals = [
            "Do not invent citations or paper authors",
            "Do not draw unsupported speculative conclusions without explicit caveat labels",
            "Do not rely solely on tertiary summaries without inspecting primary abstracts"
        ]
        milestones = [
            MilestoneParseItem(
                order_index=1,
                title="M-1: Systematic Literature Discovery & Paper Ingestion",
                description="Search academic repositories, filter by relevance and citation impact, and download primary sources.",
                dependencies=[]
            ),
            MilestoneParseItem(
                order_index=2,
                title="M-2: Comparative Analysis & Taxonomy Formulation",
                description="Extract methodology, performance metrics, and architectural patterns into structured data tables.",
                dependencies=["M-1"]
            ),
            MilestoneParseItem(
                order_index=3,
                title="M-3: Synthesis Drafting & Evidence Cross-Referencing",
                description="Write comprehensive review document citing primary sources and detailing limitations.",
                dependencies=["M-2"]
            ),
            MilestoneParseItem(
                order_index=4,
                title="M-4: Citation Verification & Deliverable Review",
                description="Validate all bibliographic entries against CrossRef/arXiv and deliver peer-ready manuscript.",
                dependencies=["M-3"]
            )
        ]
        missing_info = [
            "Date range for literature search (e.g. 2023-2026 or all-time)",
            "Target publication format (Markdown, LaTeX, IEEE style)"
        ]
        clarifying_questions = [
            "What publication or report format is required (Markdown, LaTeX, PDF)?",
            "Are there specific baseline benchmarks or datasets you want highlighted?"
        ]

    elif domain == "Healthcare Administration & Clinical Systems":
        invariants = [
            "Strict HIPAA compliance and zero plaintext PHI transmission",
            "Mandatory cryptographic audit logging for every patient data read/write",
            "Fail-safe defaults for clinical decision support or triage workflows"
        ]
        criteria = [
            "Patient data encryption at rest and in transit verified",
            "Role-based access matrix implemented (Physician, Nurse, Billing, Admin)",
            "Emergency access ('break-glass') protocol documented and auditable"
        ]
        anti_goals = [
            "Do not store unencrypted health records in application logs or cache",
            "Do not bypass patient consent validation checks",
            "Do not deploy without penetration testing verification"
        ]
        milestones = [
            MilestoneParseItem(
                order_index=1,
                title="M-1: HIPAA-Compliant Data Model & Encryption Setup",
                description="Establish encrypted persistence layer and patient record schema with field-level access control.",
                dependencies=[]
            ),
            MilestoneParseItem(
                order_index=2,
                title="M-2: Clinical Workflow Engine & Audit Trail",
                description="Implement care protocol routing, status tracking, and tamper-evident audit logging.",
                dependencies=["M-1"]
            ),
            MilestoneParseItem(
                order_index=3,
                title="M-3: Interoperability Interface & Validation",
                description="Create HL7/FHIR compliant data exchange bridges and validate schema mappings.",
                dependencies=["M-2"]
            ),
            MilestoneParseItem(
                order_index=4,
                title="M-4: Compliance Verification & Production Hardening",
                description="Run vulnerability scans, verify access controls, and certify audit compliance.",
                dependencies=["M-3"]
            )
        ]
        missing_info = ["Specific regulatory jurisdictions (US HIPAA vs EU GDPR/MDR)", "FHIR version standard"]
        clarifying_questions = ["Does the system require FHIR R4 standard compliance for external EHR integration?"]

    elif domain == "Financial Systems & FinTech":
        invariants = [
            "Double-entry ledger bookkeeping invariant (sum of debits equals sum of credits)",
            "Strict idempotent transaction execution with zero duplicate charge tolerance",
            "All currency math conducted using fixed-point decimals, never IEEE floating point"
        ]
        criteria = [
            "Transaction ledger verifies zero balance drift across stress test transactions",
            "Audit trail logs user identity, IP, timestamp, and pre/post state hash",
            "Rate limiting and fraud anomaly thresholds enforced"
        ]
        anti_goals = [
            "Do not use floating-point numbers for currency calculations",
            "Do not allow negative account balances without authorized overdraft credit line",
            "Do not execute transactions without atomic database transaction isolation"
        ]
        milestones = [
            MilestoneParseItem(
                order_index=1,
                title="M-1: Immutable Ledger Schema & Decimal Precision Engine",
                description="Set up relational double-entry ledger with atomic ACID transaction guarantees.",
                dependencies=[]
            ),
            MilestoneParseItem(
                order_index=2,
                title="M-2: Transaction Processing & Idempotency Layer",
                description="Build transaction execution API with unique idempotency keys and balance checks.",
                dependencies=["M-1"]
            ),
            MilestoneParseItem(
                order_index=3,
                title="M-3: Reconciliation Engine & Audit Reporting",
                description="Implement automated end-of-day reconciliation and discrepancy alerting.",
                dependencies=["M-2"]
            ),
            MilestoneParseItem(
                order_index=4,
                title="M-4: Financial Stress Testing & Security Audit",
                description="Execute concurrent transaction simulations and verify regulatory compliance.",
                dependencies=["M-3"]
            )
        ]
        missing_info = ["Supported currencies and multi-currency exchange rate provider", "Clearing settlement window"]
        clarifying_questions = ["Will the platform support multi-currency pairs with real-time FX rates?"]

    else:
        # Software Engineering & Architecture / General
        tech_str = f" using {', '.join(tech_set)}" if tech_set else ""
        invariants = [
            f"Must preserve backward compatibility and adhere to target stack{tech_str}",
            "Zero tolerance for unverified code deployment or skipped unit tests",
            "Strict separation of configuration credentials from source code repository",
            "All API endpoints must have validated request/response contracts"
        ]
        criteria = [
            "Core functional workflow successfully implemented and verified end-to-end",
            "Automated test coverage meets or exceeds 80% with passing unit and integration suites",
            "Comprehensive documentation and OpenAPI / README specifications generated",
            "Production-ready packaging (containerization / configuration) validated"
        ]
        anti_goals = [
            "Do not hardcode secrets, API keys, or database credentials",
            "Do not introduce unneeded tangential libraries or complex dependencies without justification",
            "Do not mock or bypass test assertions to fabricate passing builds"
        ]
        milestones = [
            MilestoneParseItem(
                order_index=1,
                title="M-1: System Architecture, Schema & Project Scaffolding",
                description="Establish repository structure, dependency configs, relational schemas, and baseline tests.",
                dependencies=[]
            ),
            MilestoneParseItem(
                order_index=2,
                title="M-2: Core Business Logic & Domain Services",
                description="Implement primary application workflows, domain entities, and data validation rules.",
                dependencies=["M-1"]
            ),
            MilestoneParseItem(
                order_index=3,
                title="M-3: Integration Testing & Security Guardrails",
                description="Execute automated integration suites, verify API contract boundaries, and stress test performance.",
                dependencies=["M-2"]
            ),
            MilestoneParseItem(
                order_index=4,
                title="M-4: Production Packaging & Acceptance Verification",
                description="Finalize documentation, containerize deployment artifacts, and conduct final acceptance signoff.",
                dependencies=["M-3"]
            )
        ]
        missing_info = [
            "Target deployment environment (e.g. Docker, Serverless, Cloud Provider)",
            "Authentication and user authorization strategy"
        ]
        clarifying_questions = [
            "What deployment infrastructure or containerization runtime is planned?",
            "What target traffic volume or performance SLA should be targeted?"
        ]

    return GoalParseResponse(
        title=title,
        intent=clean_text,
        invariant_constraints=invariants,
        acceptance_criteria=criteria,
        anti_goals=anti_goals,
        suggested_milestones=milestones,
        initial_active_milestone=milestones[0].title if milestones else "M-1: Foundation",
        missing_information=missing_info,
        clarifying_questions=clarifying_questions,
        analysis_mode="NORTHSTAR_HEURISTIC_PARSER_V2",
        detected_domain=domain
    )

class GoalParsingService:
    @staticmethod
    def parse(goal_text: str) -> GoalParseResponse:
        text = (goal_text or "").strip()
        if len(text) < 5:
            raise ValueError("Goal description is too short (minimum 5 characters). Please provide a clear description of your objective.")

        # Check if live AI provider is configured
        provider_status = ai_provider.get_provider_status()
        if provider_status.get("is_live_model", False):
            try:
                # LLM Prompt
                system_prompt = (
                    "You are the Northstar Long-Horizon Goal Decomposition Engine.\n"
                    "Analyze the user's objective and break it down into an auditable mission specification.\n"
                    "Return ONLY valid JSON matching this schema:\n"
                    "{\n"
                    '  "title": "Concise professional title (max 8 words)",\n'
                    '  "intent": "Full intent description",\n'
                    '  "detected_domain": "Domain category",\n'
                    '  "invariant_constraints": ["Constraint 1", "Constraint 2"],\n'
                    '  "acceptance_criteria": ["Criterion 1", "Criterion 2"],\n'
                    '  "anti_goals": ["Forbidden action 1", "Forbidden action 2"],\n'
                    '  "suggested_milestones": [\n'
                    '    {"order_index": 1, "title": "M-1: ...", "description": "...", "dependencies": []},\n'
                    '    {"order_index": 2, "title": "M-2: ...", "description": "...", "dependencies": ["M-1"]}\n'
                    '  ],\n'
                    '  "initial_active_milestone": "M-1: ...",\n'
                    '  "missing_information": ["Missing detail 1"],\n'
                    '  "clarifying_questions": ["Question 1"]\n'
                    "}"
                )
                raw_response = ai_provider._call_openai(
                    grounding_prompt=system_prompt,
                    session_history=[],
                    available_tools=[],
                    injected_steering=f"Goal to parse: {text}"
                )
                # Attempt to parse json from thought / action
                parsed_json = json.loads(raw_response.get("thought", "{}"))
                if "title" in parsed_json and "suggested_milestones" in parsed_json:
                    return GoalParseResponse(
                        title=parsed_json.get("title", "Autonomous Mission"),
                        intent=parsed_json.get("intent", text),
                        invariant_constraints=parsed_json.get("invariant_constraints", []),
                        acceptance_criteria=parsed_json.get("acceptance_criteria", []),
                        anti_goals=parsed_json.get("anti_goals", []),
                        suggested_milestones=[MilestoneParseItem(**m) for m in parsed_json.get("suggested_milestones", [])],
                        initial_active_milestone=parsed_json.get("initial_active_milestone", "M-1"),
                        missing_information=parsed_json.get("missing_information", []),
                        clarifying_questions=parsed_json.get("clarifying_questions", []),
                        analysis_mode=f"LIVE_LLM ({provider_status.get('model_name')})",
                        detected_domain=parsed_json.get("detected_domain", "Custom Mission")
                    )
            except Exception as e:
                logger.warning(f"Live LLM parsing failed ({e}), falling back to domain heuristic parser.")

        # Fallback to high-fidelity domain heuristic parser
        return parse_goal_heuristic(text)

goal_parsing_service = GoalParsingService()
