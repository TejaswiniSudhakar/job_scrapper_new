"""
Structured resume data for ATS-optimized LaTeX resume generation.
Fill this in once with your real information.

The generator picks bullets/skills based on what the JD asks for,
so include MANY bullet variants covering different keyword combinations.
More bullets = better ATS matching for diverse job descriptions.
"""

RESUME_DATA = {
    "name": "Nishant Chandraker",
    "email": "nishant.chandraker@example.com",
    "phone": "+91-XXXXXXXXXX",
    "location": "Bengaluru, India",
    "linkedin": "linkedin.com/in/nishant-chandraker",
    "github": "github.com/nishant73",

    "summary_templates": {
        "Backend": (
            "Java Backend Developer with {years} years of experience building scalable "
            "microservices and REST APIs using Spring Boot. Proficient in Oracle SQL, PL/SQL, "
            "and enterprise application development with Apache Tomcat. "
            "Experienced in CI/CD pipelines, Docker containerization, and Agile practices."
        ),
        "cloud_engineer": (
            "Cloud Engineer with {years} years of experience in GCP and AWS cloud services. "
            "Skilled in Docker, Kubernetes, Terraform, and CI/CD pipeline automation. "
            "Background in Java backend development and microservices architecture."
        ),
        "data_engineer": (
            "Data Engineer with {years} years of experience building data pipelines and ETL workflows. "
            "Proficient in Python, SQL, Apache Spark, and cloud data services. "
            "Background in backend development with Java and Spring Boot."
        ),
        "ML": (
            "ML Engineer with {years} years of experience in machine learning, deep learning, "
            "and data-driven applications. Skilled in Python, PyTorch, TensorFlow, and scikit-learn. "
            "Background in backend development and building production ML pipelines."
        ),
    },

    "experience": [
        {
            "title": "Software Engineer",
            "company": "Your Company Name",
            "location": "Bengaluru, India",
            "start": "Jan 2024",
            "end": "Present",
            "bullets": [
                # Backend / Java / Spring
                "Developed RESTful microservices using Java 17 and Spring Boot handling 10K+ daily API requests with sub-200ms latency",
                "Designed and implemented REST APIs with Spring MVC, Spring Security, and OAuth2 authentication",
                "Built event-driven microservices architecture using Apache Kafka for asynchronous inter-service communication",
                "Wrote complex PL/SQL stored procedures and optimized Oracle SQL queries reducing database response time by 40\\%",
                "Implemented JPA/Hibernate ORM mappings and optimized N+1 query patterns for high-throughput data access",
                # Cloud / DevOps
                "Built CI/CD pipelines using Jenkins and GitHub Actions for automated testing, Docker image builds, and deployment",
                "Containerized microservices with Docker and deployed on Kubernetes clusters using Helm charts",
                "Configured Prometheus and Grafana monitoring dashboards for service health and alerting",
                "Managed cloud infrastructure on GCP including Compute Engine, Cloud SQL, and Cloud Storage",
                # Data / Pipeline
                "Designed ETL data pipelines processing structured and semi-structured data from multiple sources",
                "Built data ingestion workflows using Python and Apache Airflow for scheduled batch processing",
                "Implemented Apache Spark jobs for large-scale data transformation and aggregation",
                # ML / Python
                "Developed Python automation scripts for data collection, transformation, and reporting",
                "Built machine learning model serving endpoints using FastAPI with Docker containerization",
                "Implemented NLP text classification pipeline using scikit-learn and sentence transformers",
                # Testing / Practices
                "Wrote unit tests with JUnit 5 and Mockito achieving 85\\% code coverage across services",
                "Practiced Agile/Scrum methodology with 2-week sprints, daily standups, and Jira tracking",
                "Conducted code reviews, pair programming sessions, and maintained Git branching strategy",
                # Distributed Systems
                "Implemented distributed caching with Redis reducing database load by 60\\% for frequently accessed data",
                "Designed fault-tolerant services with circuit breakers, retry policies, and graceful degradation",
                "Built API gateway patterns for request routing, rate limiting, and authentication",
            ],
            "tags": ["java", "spring boot", "spring", "microservices", "rest", "sql", "oracle", "pl/sql",
                     "docker", "kubernetes", "kafka", "ci/cd", "agile", "python", "redis",
                     "gcp", "jenkins", "git", "junit", "hibernate", "jpa", "monitoring",
                     "etl", "data pipeline", "spark", "airflow", "machine learning", "fastapi"],
        },
    ],

    "projects": [
        {
            "name": "Job Scraper Pipeline",
            "tech": "Python, Selenium, SQLite, Next.js, React",
            "bullets": [
                "Built an automated multi-source job scraping system collecting from LinkedIn, Naukri, and Indeed",
                "Implemented ML-based job ranking using sentence embeddings and gradient boosting",
                "Developed a real-time Next.js dashboard with AG Grid, filters, and analytics",
                "Designed queue-based processing pipeline with deduplication and automated scoring",
            ],
            "tags": ["python", "selenium", "automation", "machine learning", "react", "next.js", "sql"],
        },
        {
            "name": "Cloud Infrastructure Automation",
            "tech": "Terraform, GCP, Docker, Kubernetes, Jenkins",
            "bullets": [
                "Provisioned GCP infrastructure using Terraform with modular reusable configurations",
                "Containerized microservices with Docker and orchestrated with Kubernetes",
                "Set up CI/CD pipelines with Jenkins for automated infrastructure deployment",
                "Configured monitoring and alerting using Prometheus and Grafana",
            ],
            "tags": ["gcp", "terraform", "docker", "kubernetes", "cloud", "devops", "ci/cd", "jenkins"],
        },
        {
            "name": "Data Pipeline System",
            "tech": "Python, Apache Spark, Airflow, PostgreSQL",
            "bullets": [
                "Designed ETL pipelines processing 1M+ records daily using Apache Spark",
                "Orchestrated workflows with Apache Airflow for scheduled data ingestion",
                "Built data quality checks and monitoring dashboards for pipeline health",
                "Implemented incremental data loading with change data capture patterns",
            ],
            "tags": ["python", "spark", "airflow", "etl", "data pipeline", "postgresql", "sql"],
        },
        {
            "name": "ML Model Serving Platform",
            "tech": "Python, PyTorch, FastAPI, Docker, Redis",
            "bullets": [
                "Built a model serving platform with FastAPI for real-time inference at scale",
                "Trained and deployed NLP models for text classification using PyTorch",
                "Implemented A/B testing framework for model performance comparison",
                "Used Redis caching for prediction results reducing inference latency by 70\\%",
            ],
            "tags": ["python", "pytorch", "machine learning", "deep learning", "fastapi", "docker", "redis"],
        },
        {
            "name": "Distributed Messaging System",
            "tech": "Java, Spring Boot, Kafka, Redis, Docker",
            "bullets": [
                "Built a high-throughput messaging system using Kafka with exactly-once semantics",
                "Implemented consumer groups and partition strategies for parallel processing",
                "Designed dead-letter queue patterns for fault-tolerant message handling",
            ],
            "tags": ["java", "spring boot", "kafka", "redis", "docker", "distributed systems", "microservices"],
        },
    ],

    "education": [
        {
            "degree": "B.Tech in Computer Science",
            "institution": "Your University",
            "location": "Your City, India",
            "year": "2023",
            "gpa": "8.5/10",
        },
    ],

    "skills": {
        "languages": ["Java", "Python", "SQL", "PL/SQL", "JavaScript", "TypeScript", "Go", "Bash"],
        "frameworks": ["Spring Boot", "Spring MVC", "Spring Security", "Microservices", "REST APIs",
                       "Hibernate", "JPA", "FastAPI", "Next.js", "React"],
        "databases": ["Oracle", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite", "DynamoDB"],
        "cloud_devops": ["GCP", "AWS", "Docker", "Kubernetes", "Terraform", "Jenkins", "GitHub Actions",
                         "CI/CD", "Helm", "Prometheus", "Grafana"],
        "data_ml": ["Apache Spark", "Airflow", "Kafka", "ETL", "PyTorch", "TensorFlow",
                    "scikit-learn", "Pandas", "NumPy", "NLP"],
        "tools": ["Git", "Linux", "Jira", "Agile/Scrum", "JUnit", "Mockito", "Selenium",
                  "Tomcat", "Nginx", "Design Patterns"],
    },

    "certifications": [
        # {"name": "Google Cloud Professional Cloud Architect", "year": "2024"},
    ],
}
