def clean_job_response(jobs: list[dict]) -> str:
    """Take a raw jobs list and format it as a clean multi-line string."""
    if not jobs:
        return "No jobs found for the current search."

    cleaned_lines = []

    for i, job in enumerate(jobs[:5], start=1):
        title = job.get("title") or job.get("job_title") or "Title not provided"
        company = job.get("company") or job.get("employer") or "Company not provided"
        city = job.get("city") or job.get("location") or job.get("work_location") or "Location not provided"
        remote = job.get("remote") or job.get("remote_type") or job.get("work_model") or "Not specified"
        seniority = (
            job.get("seniority")
            or job.get("experience_level")
            or job.get("level")
            or "Not specified"
        )
        employment_type = (
            job.get("employment_type")
            or job.get("job_type")
            or job.get("type")
            or "Not specified"
        )

        salary_value = (
            job.get("salary_range")
            or job.get("salary")
            or job.get("compensation")
            or job.get("salary_range_text")
        )

        if isinstance(salary_value, dict):
            min_salary = salary_value.get("min")
            max_salary = salary_value.get("max")
            currency = salary_value.get("currency", "")
            if min_salary or max_salary:
                salary_text = f"{min_salary or 'N/A'} - {max_salary or 'N/A'} {currency}".strip()
            else:
                salary_text = "Salary not provided"
        elif salary_value:
            salary_text = str(salary_value)
        else:
            salary_text = "Salary not provided"

        link = (
            job.get("link")
            or job.get("url")
            or job.get("job_url")
            or job.get("apply_url")
            or "Link not provided"
        )

        cleaned_lines.append(
            f"{i}. {title}\n"
            f"   Company: {company}\n"
            f"   City: {city}\n"
            f"   Salary: {salary_text}\n"
            f"   Remote: {remote}\n"
            f"   Seniority: {seniority}\n"
            f"   Employment Type: {employment_type}\n"
            f"   Link: {link}\n"
        )

    return "\n".join(cleaned_lines)




