from typing import Dict, List

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

llm = OllamaLLM(model="llama3")

IMPROVEMENT_TEMPLATE = """
You are an expert AI resume coach. Provide concise, prioritized improvements across structure, content, and future development.
- Identify formatting/layout issues (e.g., missing sections, inconsistent columns, ATS blockers).
- Rewrite or enhance the provided text to highlight impact, metrics, and clarity.
- Recommend high-impact skills or learning paths relevant to the candidate's target role.
- Suggest how to better contextualize projects or roles (team size, tech stack, responsibilities).

Section: {section}
Detected Layout Columns: {columns}
Other Context: {context}
Existing Content:
{content}

Respond with:
1. Layout tweaks (skip if none).
2. Rewritten/improved text.
3. Additional skill or learning recommendations (if applicable).
4. Context amplification tips (if applicable).
"""


def _extract_sections(extracted_data: Dict) -> Dict[str, str]:
    """
    Pull section content from the extraction output.
    """
    sections = extracted_data.get("sections")
    if isinstance(sections, dict) and sections:
        return {
            section_name: str(section_content)
            for section_name, section_content in sections.items()
            if section_content
        }

    # Fallback to raw text as a single section
    raw_text = extracted_data.get("raw_text") or extracted_data.get("text") or ""
    return {"resume_body": str(raw_text)}


def _section_context(extracted_data: Dict) -> Dict[str, str]:
    """
    Provide additional context for each section (skills, layout info, etc.).
    """
    context: Dict[str, str] = {}
    metadata = extracted_data.get("metadata", {})

    layout = metadata.get("layout") or extracted_data.get("layout")
    if isinstance(layout, dict):
        columns = layout.get("columns")
        if columns:
            context["columns"] = f"{columns} columns detected"

    top_skills = extracted_data.get("skills")
    if isinstance(top_skills, list) and top_skills:
        context["skills"] = ", ".join(
            [skill for skill in top_skills if isinstance(skill, str)][:10]
        )

    target_role = metadata.get("target_role")
    if isinstance(target_role, str):
        context["target_role"] = target_role

    return context


async def get_section_suggestions(extracted_data: dict) -> List[Dict]:
    """
    Generate AI suggestions for each section, covering layout, writing quality, skill gaps, and project context.
    """
    sections = _extract_sections(extracted_data)
    context = _section_context(extracted_data)
    columns = context.get("columns", "unknown")
    skills = context.get("skills", "Not specified")
    target_role = context.get("target_role", "Not specified")

    prompt = PromptTemplate.from_template(IMPROVEMENT_TEMPLATE)

    suggestions: List[Dict] = []

    for section_name, content in sections.items():
        if not content.strip():
            continue

        # Real call (uncomment when ready)
        # Example for future live call using LCEL:
        # from langchain_core.output_parsers import StrOutputParser
        # chain = prompt | llm | StrOutputParser()
        # response = await chain.ainvoke({
        #     "section": section_name,
        #     "columns": columns,
        #     "context": f"Skills: {skills}; Target Role: {target_role}",
        #     "content": content,
        # })

        # Placeholder response for now
        response = (
            f"Layout: Consider consistent spacing and clear column separation if {columns}.\n"
            f"Rewrite: Strengthen impact statements for {section_name}. "
            f"Highlight quantified achievements.\n"
            f"Skills: Consider adding modern tools relevant to {target_role}. "
            f"Current skills noted: {skills}.\n"
            f"Context: Specify your role, team size, and outcomes for key projects."
        )

        suggestions.append(
            {
                "section": section_name,
                "old_text": content,
                "suggestion": response,
            }
        )

    # Global recommendations leveraging metadata
    global_recos = []
    if "columns" not in context:
        global_recos.append(
            "Specify consistent layout (one or two columns). Uneven spans can confuse ATS."
        )
    if skills == "Not specified":
        global_recos.append("Add a dedicated skills section covering technical and soft skills.")
    if target_role == "Not specified":
        global_recos.append("Mention the target role or headline to align the resume focus.")

    if global_recos:
        suggestions.append(
            {
                "section": "overall",
                "old_text": "",
                "suggestion": "\n".join(global_recos),
            }
        )

    return suggestions