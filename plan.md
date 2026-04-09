# Project Proposal: Course Selection Agent for NUS

**Authors:** Wu Lyucheng, Gao Yiwen, Zhao Haochen, Zhang Haotian

---

## 1. Motivation & Problem Statement

### 1.1 Background
Course selection at the National University of Singapore (NUS) is primarily a **decision-making** problem rather than a pure scheduling problem. Students must first decide which courses are most suitable for their goals before resolving detailed timetable arrangements. However, making these decisions is non-trivial because course-related information is fragmented across multiple platforms, including CourseReg, NUSMods, official course webpages, and informal discussion channels. 

In addition, students optimize for fundamentally different objectives:
* **GPA-oriented:** Prioritizing lighter workloads or lenient grading.
* **Knowledge-oriented:** Prioritizing intellectual depth and skill acquisition.
* **Logistical preferences:** Tolerance for workload intensity, assessment frequency, and teaching styles.

Existing tools like NUSMods mainly support timetable visualization, offering limited help for **pre-scheduling** decision-making. Consequently, students often rely on incomplete heuristics, leading to suboptimal selections.

### 1.2 Problem Definition
We formulate course selection as a **preference-aware recommendation** problem under both soft and hard constraints. 

**Core Research Question:**
> *How can we design an interactive AI agent that recommends the most suitable courses for a student by reasoning over heterogeneous course attributes and personalized preferences, while treating timetable constraints as soft, adjustable factors?*

---

## 2. Project Objective
The objective is to implement a course recommendation agent that assists students *before* detailed timetable construction. The agent aims to:

1.  **Capture student profiles:** Model academic background, learning objectives, and trade-offs (e.g., GPA vs. rigor).
2.  **Aggregate course information:** Retrieve and normalize data from multiple sources (content, assessments, instructor policies).
3.  **Perform preference-aware reasoning:** Rank courses by computing utility based on student objectives.
4.  **Generate interpretable recommendations:** Provide evidence-based explanations and highlight potential drawbacks.

---

## 3. System Overview

### 3.1 Agent Capabilities
* **Intent Modeling:** Interpret natural-language requests and infer implicit preferences.
* **Tool-Grounded Retrieval:** Access authoritative facts from NUSMods to mitigate hallucinations.
* **Constraint-Aware Recommendation:** Enforce prerequisites as hard constraints while optimizing for soft constraints (e.g., schedule friction).

### 3.2 System Architecture
* **Frontend:** Chat-style web UI for natural language interaction.
* **Backend:** LLM agent (GPT/Gemini) using a ReAct-style workflow.
* **Tool Layer:** Services for course search, prerequisite validation, and conflict checking.
* **Memory:** Short-term session history and optional long-term preference storage.

---

## 4. Agent Design (Core Technical Contribution)

### 4.1 Agent Framework
* **ReAct-style reasoning:** Iterate through Plan $\rightarrow$ Tool Call $\rightarrow$ Evidence Aggregation $\rightarrow$ Response.
* **Multi-step orchestration:** Support pipelines like *Search* $\rightarrow$ *Prerequisites* $\rightarrow$ *Ranking*.

### 4.2 Tool Interfaces
* **CourseSearchTool:** Metadata retrieval (credits, instructors, etc.).
* **PrerequisiteValidator:** Hard constraint checking for module eligibility.
* **TimetableConflictChecker:** Computes "schedule friction" scores.

---

## 5. Implementation Framework (n8n-based)

### 5.1 High-Level Architecture
We use **n8n** as the orchestration layer to route requests, call the LLM, invoke tools, and maintain state.

### 5.2 Workflow Decomposition
* **Main Workflow:** Handles input processing, preference extraction, planning, and final explanation generation.
* **Sub-Workflows:** Independent tools (Search, Validator, etc.) exposed via HTTP interfaces.

### 5.3 Preference-Aware Ranking
Recommendation is modeled as utility-based ranking. While the LLM explains trade-offs, **deterministic scoring** is used for ranking to ensure stability and reproducibility.

---

## 6. Evaluation Plan

### 6.1 Methodology
Comparative evaluation between the **n8n agent** and a **base LLM** (without tools) using a "NUS Selection Benchmark."

### 6.2 Quantitative Metrics

| Metric                     | Definition                                       | Goal               |
| :------------------------- | :----------------------------------------------- | :----------------- |
| **Information Accuracy**   | % of facts matching ground truth (NUSMods)       | Zero hallucination |
| **Constraint Violation**   | Frequency of recommending invalid prerequisites  | < 5%               |
| **Tool-Use Precision**     | Accuracy of selecting the correct sub-workflow   | > 90%              |
| **Reasoning Transparency** | Whether explanations cite tool-provided evidence | Qualitative        |

### 6.3 Human-in-the-Loop
A blind A/B test with NUS students to rank outputs by trustworthiness, relevance, and logical soundness.
