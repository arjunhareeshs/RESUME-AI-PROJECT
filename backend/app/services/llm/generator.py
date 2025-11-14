from typing import Dict, Tuple, List, Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from ...schemas.resume import ResumeGenerationRequest

llm = OllamaLLM(model="llama3")

GENERATION_TEMPLATE = """
You are an elite ATS-focused resume writer. Build a resume that:
- Fixes every weakness noted in the reviewer feedback (layout, skills, context, formatting).
- Uses clean structure with standard sections (Summary, Key Skills, Experience, Education, Projects, Certifications, Languages, Achievements).
- Keeps a consistent one or two-column layout, clear headings, and bullet points that start with action verbs.
- Highlights impact with quantified metrics and relevant tools.
- Incorporates must-have skills and learning recommendations when provided.
- Embeds context for each role/project (team size, responsibilities, technologies, outcomes).
- Remains concise (preferably < 2 pages) and ATS keyword rich without keyword stuffing.

Candidate Details:
Name: {name}
Target Role: {role}
Existing Summary: {existing_summary}
Top Skills: {skills}
Required / Suggested Skills: {recommended_skills}
Education:
{education}
Projects:
{projects}
Experience Blocks:
{experience}
Languages: {languages}
Certifications: {certifications}
Awards & Honors: {awards}
Volunteer Work: {volunteer}
Interests: {interests}
Career Goals or Notes: {career_context}

Detected Layout Notes: {layout_notes}
Known Weaknesses To Address:
{improvement_feedback}

Output the final resume text only. Use Markdown-friendly formatting with clear section headers.
"""


def _format_education(education: List[Dict]) -> str:
    lines = []
    for entry in education:
        degree = entry.get("degree", "")
        school = entry.get("school", "")
        start = entry.get("start", "")
        end = entry.get("end", "")
        location = entry.get("location", "")
        details = ", ".join(filter(None, [start, end, location]))
        line = f"- {degree} at {school}"
        if details:
            line += f" ({details})"
        extra = entry.get("notes") or entry.get("achievements")
        if extra:
            line += f" — {extra}"
        lines.append(line)
    return "\n".join(lines) if lines else "N/A"


def _format_projects(projects: List[Dict]) -> str:
    lines = []
    for project in projects:
        name = project.get("name", "Project")
        description = project.get("description", "")
        role = project.get("role")
        impact = project.get("impact")
        technologies = project.get("technologies")
        sentence = f"- {name}: {description}"
        if role:
            sentence += f" | Role: {role}"
        if technologies:
            sentence += f" | Tech: {', '.join(technologies)}" if isinstance(technologies, list) else f" | Tech: {technologies}"
        if impact:
            sentence += f" | Impact: {impact}"
        lines.append(sentence)
    return "\n".join(lines) if lines else "N/A"


def _format_experience(experience: List[Dict]) -> str:
    lines = []
    for exp in experience:
        company = exp.get("company", "Company")
        role = exp.get("title") or exp.get("role", "Role")
        start = exp.get("start")
        end = exp.get("end") or "Present"
        location = exp.get("location", "")
        header = f"- {role}, {company} ({start} – {end}"
        if location:
            header += f", {location}"
        header += ")"
        lines.append(header)
        bullet_points = exp.get("bullets") or exp.get("summary") or exp.get("responsibilities") or []
        if isinstance(bullet_points, str):
            bullet_points = [bullet_points]
        for bullet in bullet_points:
            lines.append(f"  • {bullet}")
        achievements = exp.get("achievements")
        if achievements:
            if isinstance(achievements, list):
                for ach in achievements:
                    lines.append(f"  • Achievement: {ach}")
            else:
                lines.append(f"  • Achievement: {achievements}")
    return "\n".join(lines) if lines else "N/A"


def _collapsed_list(items) -> str:
    if not items:
        return "N/A"
    if isinstance(items, list):
        return ", ".join(str(item) for item in items if item)
    return str(items)


def _format_volunteer(volunteer: Optional[List[Dict]]) -> str:
    if not volunteer:
        return "N/A"
    lines: List[str] = []
    for entry in volunteer:
        organization = entry.get("organization", "Organization")
        role = entry.get("role") or entry.get("title", "")
        description = entry.get("description", "")
        line = f"- {role} at {organization}"
        if description:
            line += f": {description}"
        lines.append(line)
    return "\n".join(lines) if lines else "N/A"


async def generate_resume_from_data(
    request: ResumeGenerationRequest,
    improvement_feedback: str = "",
    layout_notes: str = "",
    recommended_skills: Optional[List[str]] = None,
    career_context: str = "",
) -> Tuple[str, Dict]:
    """
    Generates an ATS-optimized resume text using candidate data plus improvement hints.
    """
    prompt = PromptTemplate.from_template(GENERATION_TEMPLATE)

    payload: Dict = request.dict()

    payload["role"] = request.target_role or request.role
    payload["skills"] = _collapsed_list(request.skills)
    payload["education"] = _format_education(payload.get("education", []))
    payload["projects"] = _format_projects(payload.get("projects", []))
    payload["experience"] = _format_experience(payload.get("experience", []))
    payload["languages"] = _collapsed_list(payload.get("languages"))
    payload["certifications"] = _collapsed_list(payload.get("certifications"))
    payload["awards"] = _collapsed_list(payload.get("awards"))
    payload["volunteer"] = _format_volunteer(payload.get("volunteer"))
    payload["interests"] = _collapsed_list(payload.get("interests"))
    payload["existing_summary"] = request.summary or "Not provided."
    payload["recommended_skills"] = _collapsed_list(recommended_skills)
    payload["improvement_feedback"] = improvement_feedback or "None provided."
    payload["layout_notes"] = layout_notes or "Standard single column."
    payload["career_context"] = career_context or "Not specified."

    # Uncomment when ready for live generation
    # Example for future use when enabling LLM call:
    # from langchain.chains import LLMChain
    # chain = LLMChain(llm=llm, prompt=prompt)
    # resume_text = await chain.arun(**payload)

    resume_text = (
        f"{request.name}\n{request.role}\n\n"
        "Summary\n"
        "Driven professional ready to deliver impact. (LLM generation placeholder)\n"
    )

    structured = {
        "candidate": {
            "name": request.name,
            "role": payload["role"],
        },
        "skills": request.skills,
        "summary": request.summary,
        "education": payload.get("education"),
        "experience": payload.get("experience"),
        "projects": payload.get("projects"),
        "languages": payload.get("languages"),
        "certifications": payload.get("certifications"),
        "awards": payload.get("awards"),
        "volunteer": payload.get("volunteer"),
        "interests": payload.get("interests"),
        "recommendations": {
            "improvement_feedback": improvement_feedback,
            "recommended_skills": recommended_skills or [],
            "layout_notes": layout_notes,
            "career_context": career_context,
        },
    }

    return resume_text, structured

