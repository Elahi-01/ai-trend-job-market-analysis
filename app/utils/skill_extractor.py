"""
Extracts technical and professional skills from job text.
"""
import re
from typing import List


class SkillExtractor:
    TECH_SKILLS = {
        # Languages
        'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
        'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Dart', 'Perl',
        # Frontend
        'React', 'Vue', 'Angular', 'Next.js', 'Nuxt.js', 'Svelte', 'HTML', 'CSS',
        'SASS', 'Tailwind', 'Bootstrap', 'Redux', 'GraphQL',
        # Backend
        'Node.js', 'Django', 'Flask', 'FastAPI', 'Spring', 'Laravel', 'Rails',
        'Express', 'NestJS', 'ASP.NET', 'Gin', 'Fiber',
        # Databases
        'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch', 'Cassandra',
        'DynamoDB', 'SQLite', 'Oracle', 'SQL Server', 'Firebase', 'Supabase',
        # Cloud
        'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'Ansible',
        'Jenkins', 'CircleCI', 'GitHub Actions', 'Vercel', 'Heroku', 'Render',
        # ML/AI
        'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Keras',
        'OpenCV', 'NLTK', 'spaCy', 'Hugging Face', 'LangChain', 'OpenAI',
        # Tools
        'Git', 'Linux', 'Nginx', 'Apache', 'RabbitMQ', 'Kafka', 'Celery',
        'Airflow', 'dbt', 'Spark', 'Hadoop', 'Tableau', 'Power BI',
        # Methodologies
        'REST', 'API', 'Microservices', 'CI/CD', 'DevOps', 'Agile', 'Scrum',
        'TDD', 'BDD', 'SOA', 'Event-driven', 'Serverless'
    }

    def __init__(self):
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> List[re.Pattern]:
        patterns = []
        for skill in self.TECH_SKILLS:
            escaped = re.escape(skill)
            pattern = re.compile(
                rf'\b{escaped}\b',
                re.IGNORECASE
            )
            patterns.append((skill, pattern))
        return patterns

    def extract_from_text(self, text: str) -> List[str]:
        """Extract skills from text, returning canonical skill names."""
        if not text:
            return []
        found = set()
        for canonical, pattern in self._patterns:
            if pattern.search(text):
                found.add(canonical)
        return sorted(list(found))

    def extract_from_list(self, texts: List[str]) -> List[str]:
        combined = ' '.join(texts)
        return self.extract_from_text(combined)