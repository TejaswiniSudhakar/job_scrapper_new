"""
Structured resume data for ATS-optimized LaTeX resume generation.
Fill this in once with your real information.

The generator picks bullets/skills based on what the JD asks for,
so include MANY bullet variants covering different keyword combinations.
More bullets = better ATS matching for diverse job descriptions.
"""

RESUME_DATA = {
    "name": "Nishant Chandraker",
    "email": "nishant31.chandraker@example.com",
    "phone": "+91-9757064016",
    "location": "Bengaluru, India",
    "linkedin": "https://www.linkedin.com/in/nishant-chandraker-93750b206/",
    "github": "https://github.com/nishant73",

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
            "title": "System Engineer",
            "company": "Tata Consultancy Services",
            "location": "Bengaluru, India",
            "start": "Aug 2024",
            "end": "Dec 2025",
            "bullets": [
                # Backend / Java / Spring
                "Developed and enhanced backend data processing modules using Java, Spring Boot, and PL/SQL, supporting financial systems handling 100K+ records per day",
                "Designed and implemented RESTful microservices with Spring MVC, Spring Security, and OAuth2 for secure inter-service communication",
                "Built event-driven microservices architecture using Apache Kafka for asynchronous processing and real-time data streaming",
                "Wrote complex PL/SQL stored procedures, triggers, and batch workflows, optimizing Oracle SQL queries and reducing execution time by 25--35\\%",
                "Implemented JPA/Hibernate ORM mappings and resolved N+1 query patterns, improving high-throughput data access performance",
                "Developed RESTful APIs handling 10K+ daily requests with sub-200ms latency using Spring Boot and Apache Tomcat",
                # Data / Pipeline / ETL
                "Designed and maintained ETL data pipelines processing structured and semi-structured data from multiple upstream sources",
                "Built data ingestion and transformation workflows using Python and Apache Airflow for scheduled batch processing",
                "Implemented Apache Spark jobs for large-scale data transformation, aggregation, and data quality validation",
                "Built reusable validation and transformation logic across data products, reducing data inconsistencies by approximately 30\\%",
                "Contributed to end-to-end feature enhancements across 3+ data products, from requirement analysis through deployment",
                # Cloud / DevOps
                "Built CI/CD pipelines using Jenkins and GitHub Actions for automated testing, Docker image builds, and production deployment",
                "Containerized microservices with Docker and deployed on Kubernetes clusters using Helm charts and rolling updates",
                "Managed cloud infrastructure on GCP including Compute Engine, Cloud SQL, Cloud Storage, and Cloud Functions",
                "Configured Prometheus and Grafana monitoring dashboards for service health, performance metrics, and alerting",
                "Provisioned infrastructure using Terraform with modular reusable configurations for reproducible environments",
                # ML / Python / Automation
                "Developed Python automation scripts for data collection, transformation, reporting, and web scraping workflows",
                "Built machine learning model serving endpoints using FastAPI with Docker containerization and Redis caching",
                "Implemented NLP text classification pipeline using scikit-learn, sentence transformers, and custom feature engineering",
                "Automated batch processing jobs and report generation, reducing manual intervention and improving reliability",
                # Testing / Practices / Collaboration
                "Wrote unit tests with JUnit 5 and Mockito achieving 85\\% code coverage across microservices",
                "Practiced Agile/Scrum methodology with 2-week sprints, daily standups, sprint retrospectives, and Jira tracking",
                "Conducted code reviews, pair programming sessions, and maintained Git branching strategy with pull request workflows",
                "Collaborated with 5+ cross-functional stakeholders including business analysts, QA, and frontend teams",
                "Resolved 15+ production issues by performing root cause analysis, debugging, and implementing long-term fixes",
                # Distributed Systems / Architecture
                "Implemented distributed caching with Redis reducing database load by 60\\% for frequently accessed data",
                "Designed fault-tolerant services with circuit breakers, retry policies, graceful degradation, and dead-letter queues",
                "Built API gateway patterns for request routing, rate limiting, load balancing, and centralized authentication",
                "Improved system observability through structured logging, distributed tracing, and validation checks, reducing debugging time by 20\\%",
                # Database
                "Designed normalized relational database schemas and optimized indexing strategies for high-performance data retrieval",
                "Managed database migrations, schema versioning, and data integrity constraints across multiple environments",
                "Implemented connection pooling, query optimization, and read replicas for scalable database architecture",
            ],
            "tags": ["java", "spring boot", "spring", "microservices", "rest", "sql", "oracle", "pl/sql",
                     "docker", "kubernetes", "kafka", "ci/cd", "agile", "python", "redis",
                     "gcp", "jenkins", "git", "junit", "hibernate", "jpa", "monitoring",
                     "etl", "data pipeline", "spark", "airflow", "machine learning", "fastapi",
                     "terraform", "helm", "prometheus", "grafana", ".net", "tomcat",
                     "distributed systems", "api gateway", "elasticsearch"],
        },
        {
            "title": "Software Developer Intern",
            "company": "Bhabha Atomic Research Centre",
            "location": "Mumbai, India",
            "start": "May 2023",
            "end": "Jul 2023",
            "bullets": [
                "Designed and implemented a normalized relational database schema to efficiently manage employee data across multiple departments",
                "Developed RESTful backend services using Spring Boot for seamless frontend-backend communication and data exchange",
                "Implemented business logic for validation, retrieval, and transformation across multiple application modules",
                "Optimized database queries and indexing strategies, improving data retrieval performance by 30\\%",
                "Participated in designing modular service architecture for scalability, maintainability, and separation of concerns",
                "Built automated data validation pipelines ensuring data integrity and consistency across systems",
                "Wrote comprehensive unit and integration tests using JUnit and Mockito for backend services",
                "Collaborated with senior engineers on system design decisions and participated in code review processes",
            ],
            "tags": ["java", "spring boot", "rest", "sql", "database", "junit", "mockito",
                     "backend", "microservices", "testing", "agile"],
        },
    ],

    "projects": [
        {
            "name": "Data Pipeline Orchestration Platform",
            "tech": "Python, Apache Airflow, Docker, PostgreSQL",
            "bullets": [
                "Built automated ETL pipelines for data ingestion, transformation, and validation workflows processing 1M+ records daily",
                "Designed DAG-based orchestration with dependency management, retries, failure recovery, and SLA monitoring",
                "Automated batch processing jobs with scheduling, reducing manual intervention and improving data freshness",
                "Implemented centralized logging, monitoring, and alerting for pipeline observability and debugging",
                "Containerized pipeline components using Docker for reproducible execution across environments",
                "Developed modular workflows supporting scalable data processing with incremental loading patterns",
                "Built data quality checks with automated validation rules and anomaly detection",
            ],
            "tags": ["python", "airflow", "etl", "data pipeline", "docker", "postgresql", "sql", "automation", "monitoring"],
        },
        {
            "name": "Cloud-Native Data Processing Platform",
            "tech": "GCP (Cloud Run, Cloud Storage, Cloud Functions), Node.js, Firestore, CI/CD",
            "bullets": [
                "Built a scalable cloud-based data processing system handling over 10K records and file uploads with auto-scaling",
                "Designed event-driven workflows using Cloud Functions for automated processing and real-time triggers",
                "Deployed services on Cloud Run with auto-scaling capabilities and zero-downtime deployments",
                "Implemented CI/CD pipelines using GitHub Actions for automated testing, building, and deployment",
                "Improved system performance through caching, CDN integration, and optimized storage access patterns",
                "Applied access control, IAM policies, and security best practices for data protection and compliance",
                "Designed serverless architecture reducing infrastructure costs by 40\\% compared to VM-based approach",
            ],
            "tags": ["gcp", "cloud", "serverless", "ci/cd", "github actions", "docker", "node.js", "firestore"],
        },
        {
            "name": "Recommendation Analytics Pipeline",
            "tech": "Python, PostgreSQL, FastAPI, MLflow, Docker",
            "bullets": [
                "Built end-to-end data pipelines for collecting, transforming, and serving recommendation data at scale",
                "Performed feature engineering and preprocessing on user interaction datasets with 500K+ records",
                "Designed modular workflows covering ingestion, validation, training, and deployment stages",
                "Implemented experiment tracking and model versioning using MLflow for reproducible ML workflows",
                "Stored and managed analytical datasets in PostgreSQL with optimized schemas for reporting",
                "Automated deployment workflows using Docker and CI/CD pipelines with health checks",
                "Built REST API endpoints using FastAPI for real-time model inference with sub-100ms latency",
            ],
            "tags": ["python", "postgresql", "fastapi", "machine learning", "docker", "ci/cd", "etl", "data pipeline"],
        },
        {
            "name": "Job Scraper Pipeline",
            "tech": "Python, Selenium, SQLite, Next.js, React",
            "bullets": [
                "Built an automated multi-source job scraping system collecting from LinkedIn, Naukri, and Indeed with deduplication",
                "Implemented ML-based job ranking using sentence embeddings, gradient boosting classifier, and custom feature engineering",
                "Developed a real-time Next.js dashboard with AG Grid, advanced filters, analytics charts, and export functionality",
                "Designed queue-based processing pipeline with concurrent scrapers, deduplication, and automated scoring",
                "Built ATS-optimized resume generator that tailors content to each job description using keyword matching",
                "Implemented web scraping automation with Selenium, undetected-chromedriver, and anti-bot detection handling",
            ],
            "tags": ["python", "selenium", "automation", "machine learning", "react", "next.js", "sql", "web scraping"],
        },
        {
            "name": "Distributed Messaging System",
            "tech": "Java, Spring Boot, Kafka, Redis, Docker",
            "bullets": [
                "Built a high-throughput messaging system using Kafka with exactly-once semantics handling 50K+ messages/minute",
                "Implemented consumer groups and partition strategies for parallel processing and horizontal scaling",
                "Designed dead-letter queue patterns for fault-tolerant message handling and error recovery",
                "Integrated Redis caching layer for message deduplication and idempotent processing",
                "Containerized services with Docker Compose for local development and Kubernetes for production",
                "Implemented monitoring with Prometheus metrics and Grafana dashboards for throughput and lag tracking",
            ],
            "tags": ["java", "spring boot", "kafka", "redis", "docker", "distributed systems", "microservices"],
        },
    ],

    "education": [
        {
            "degree": "B.Tech in Computer Science",
            "institution": "Vellore Institute of Technology (VIT), Vellore",
            "location": "Vellore, TN, India",
            "year": "2020 - 2024",
            "gpa": "7.44/10",
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
