from dataclasses import dataclass

@dataclass
class MaterialDraft:
    """Represent metadata for a resource before it is stored."""
    title: str
    category: str
    semester: str
    section: str

    def validate(self):
        allowed = {"Notes", "Exam/Syllabus", "Assignment", "Project", "Practical/Lab", "Other"}
        if not self.title.strip():
            raise ValueError("Title is required.")
        if self.category not in allowed:
            raise ValueError("Invalid category.")
        if not self.semester.strip() or not self.section.strip():
            raise ValueError("Semester and section are required.")
        return True
