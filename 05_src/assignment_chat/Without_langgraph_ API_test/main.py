from openai import OpenAI
from dotenv import load_dotenv
from assignment_chat.prompts import return_instructions_root
from assignment_chat.normalize import normalize_location
import json
import requests
from utils.logger import get_logger
from utils.clients import get_client
import os


_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")


client = get_client()

open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


#The descritpion is what is used  by the model to get the args for the tool call
tools = [
    {
        "type": "function",
        "name": "get_job_listings",
        "description": "This tool retrieves job listings for a given set of job search keywords",
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": 'Only the job title, not the full user message. Example: "Data Scientist" , "Data Scientist OR Machine Learning Engineer" in case of multiple job titles .',
                },
                # "region": {
                #     "type": "string",
                #     "description": 'Specifies the region like a canadain province or provinces and not the city for the job listings search such as Ontario (CA-ON), US-NY, defaults to "CA-ON".',
                #     "default": "CA-ON"
                # },
                "city": {
                    "type": "string",
                    "description": 'Specifies the city for the job listings search such as Toronto, Montreal, this can be multiple cities comma separated as well like "Toronto, Montreal", defaults to "Toronto".',
                    "default": "Toronto"
                },
                # "country": {
                #     "type": "string",
                #     "description": 'Specifies the country for the job listings search such as CA, USA, defaults to "CA".',
                #     "default": "CA"
                # },
                "remote": {
                    "type": "string",
                    "description": 'Specifies the job type for the job listings search such as remote, hybrid, defaults to "hybrid".',
                    "default": "hybrid"
                },
                "seniority": {
                    "type": "string",
                    "description": 'Specifies the seniority level for the job listings search such as entry, mid, senior defaults to "mid,senior".',
                    "default": "mid,senior"
                },
                "limit": {
                    "type": "integer", #This was bug as I had 'int' 
                    "description": 'Specifies the number of results for job listings search defaults to 5.',
                    "default": 5
                },

            },
            "required": ["title"],
            "additionalProperties": False
        },
        
    },
]



def get_job_listings(
    title: str,
    # region: str = "Ontario",
    city: str = "Toronto",
    remote: str = "hybrid",
    seniority: str = "mid,senior",
    # country: str = "Canada",
    limit: int = 5,
) -> str:
    """
    An API call to the job opportunites api us made
    The API call is to https://jobopportunitiesapi.org/
    takes multiple job search params
    """
    
    cleaned_job_str = fetch_jobs_for_title(
        title,
        # region,
        city,
        remote,
        seniority,
        # country,
        limit
        ) 
    return cleaned_job_str



def fetch_jobs_for_title(
    title: str,
    # region: str = "Ontario",
    city:str = "Toronto",
    remote = "hybrid",
    seniority: str = "Mid,Senior",
    # country: str = "Canada",
    limit: int = 5,
) -> str:
    """Fetch job listings for a title and normalize the results into a readable string."""
    if not title or not title.strip():
        return "Please provide a job title to search for."

    #Convert country and region to ISO8 for the API
    
    # print(f"Country & region before ISO8 : {country} & {region}")
    country, region, or_city = normalize_location(
        city = city #This can be a lit if cities as well
    )
    print(f"Country & region codes extracted from cities: {country} & {region} for {or_city}")

    if limit > 5:
        print(f"Limit was {limit}. Reducing it to 5 to stay within the allowed maximum.")
        limit = 5

    base_url = globals().get("BASE_URL", "https://api.jobopportunitiesapi.org")
    request_headers = globals().get("headers", {"Accept": "application/json"})
    api_key = os.getenv("JOB_API")
    if api_key:
        request_headers = {**request_headers, "Authorization": f"Bearer {api_key}"}

    attempts = [
        {
            "country": country,
            "title": title,
            "region": region,
            "city": or_city,
            "remote": remote,
            "seniority": seniority,
            "limit": limit,
        },
        {
            "country": country,
            "title": title,
            "region": region,
            "limit": limit,
        },
        {
            "country": country,
            "title": title,
            "limit": limit,
        },
    ]

    for idx, params in enumerate(attempts, start=1):
        clean_params = {k: v for k, v in params.items() if v is not None and v != ""}

        try:
            response = requests.get(
                f"{base_url}/v1/jobs",
                headers=request_headers,
                params=clean_params,
                timeout=30,
            )
            print(f"API returned {response.status_code} on attempt {idx}, params {clean_params}")
        except requests.RequestException as exc:
            print(f"Request failed on attempt {idx}: {exc}")
            continue

        if response.status_code != 200:
            print(f"API returned {response.status_code} on attempt {idx}, params {clean_params}")
            continue

        try:
            payload = response.json()
        except ValueError:
            print(f"API rclean_paramse on attempt {idx} was not valid JSON.")
            continue

        jobs = payload.get("data")
        if jobs is None:
            jobs = payload.get("jobs") or []

        if jobs:
            return clean_job_response(jobs)

        print(
            f"Successful response on attempt {idx}, but data was empty []. "
            "Retrying with a looser filter set."
        )

    return (
        "No jobs were found for this search. "
        "Please try a different job title, region, country, or remote preference."
    )


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



def extract_text_content(content) -> str:
    """
    Gradio's Chatbot normalizes string content into a list of parts like
    [{"type": "text", "text": "..."}], which the Responses API does not accept
    as-is. Flatten back down to plain text.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return "" if content is None else str(content)


def sanitize_history(history: list[dict]) -> list[dict]:
    clean_history = []
    for msg in history:
        clean_history.append({
            "role": msg.get("role"),
            "content": extract_text_content(msg.get("content"))
        })
    return clean_history


def assignment_chat(message: str, history: list[dict] = []) -> str:
    #Main function
    _logs.info(f'User message: {message}')
    
    instructions = return_instructions_root()
    
    user_msg = {
        "role": "user",
        "content": message
    }
    
    conversation_input = sanitize_history(history) + [user_msg]
    
    response = client.responses.create(
        model=open_ai_model,  
        instructions=instructions,
        input=conversation_input,
        tools=tools,
        
    )
    
    conversation_input += response.output

    # Handle function calls if any
    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_job_listings":
                args = json.loads(item.arguments)
                _logs.info(f'Function call args: {args}')
                
                # Call the job listings function
                op_result = get_job_listings(**args)
                
                # Add function call result to conversation
                
                func_call_output = {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({
                        "job_listings": op_result
                    })
                }
                
                _logs.debug(f"Function call output: {func_call_output}")

                conversation_input = conversation_input + [func_call_output]
                
                # Make second API call with function result
                response = client.responses.create(
                    model=open_ai_model,
                    instructions=instructions,
                    tools=tools,
                    input=conversation_input
                )
                break
    
    
    return response.output_text




