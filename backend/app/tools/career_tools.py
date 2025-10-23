import os
import json
import asyncio
from typing import Dict, Any
import tavily

def get_career_insights(field: str) -> Dict[str, Any]:
    """
    Search for career insights and job market trends using Tavily search API.

    This tool provides real-time information about:
    - Job market trends and demand
    - Salary expectations and ranges
    - Required skills and qualifications
    - Career growth opportunities
    - Industry insights and outlook

    Args:
        field (str): The career field or profession to research (e.g., "AI engineering", "software development", "data science")

    Returns:
        Dict[str, Any]: Search results with career information
    """
    try:
        # Get Tavily API key from environment
        tavily_api_key = os.getenv("TAVILY_API_KEY")

        if not tavily_api_key:
            return {
                "success": False,
                "error": "TAVILY_API_KEY not configured",
                "query": field,
                "message": "Tavily API key is required. Please add TAVILY_API_KEY to your .env file.",
                "mock_data": {
                    "field": field,
                    "job_growth": "High demand expected",
                    "average_salary": "$90,000 - $150,000",
                    "key_skills": ["Python", "Machine Learning", "APIs", "Problem Solving"],
                    "outlook": "Strong growth prospects"
                }
            }

        # Initialize Tavily client
        tavily_client = tavily.TavilySearch(api_key=tavily_api_key)

        # Search for career insights
        search_query = f"latest career insights job market trends salary opportunities for {field}"

        # Perform search
        # For simplicity in testing, do synchronous call
        response = tavily_client.search(search_query, search_depth="advanced", include_answer=True)

        if not response or not response.get('results'):
            return {
                "success": False,
                "error": "No search results returned",
                "query": field,
                "message": f"No career insights found for: {field}"
            }

        # Extract relevant information
        results = response.get('results', [])

        # Format the response
        insights = {
            "field": field,
            "query": search_query,
            "results_count": len(results),
            "insights": []
        }

        # Process top 3 results
        for i, result in enumerate(results[:3]):
            title = result.get('title', 'Career Insight')
            content = result.get('content', '')
            url = result.get('url', '')

            insights.append({
                "title": title,
                "summary": content[:200] + '...' if len(content) > 200 else content,
                "source": url,
                "relevance_score": 3 - i  # Simple scoring based on position
            })

        # Add general field recommendations
        field_lower = field.lower()
        if 'software' in field_lower or 'developer' in field_lower:
            insights.append({
                "title": "Essential Skills",
                "summary": "Strong programming skills in Python, JavaScript, and cloud platforms. Experience with version control and agile methodologies.",
                "source": "industry_standard",
                "relevance_score": 10
            })
        elif 'data' in field_lower or 'ai' in field_lower:
            insights.append({
                "title": "Market Demand",
                "summary": "High demand for AI/ML professionals. Companies seeking expertise in machine learning, data analysis, and cloud deployment.",
                "source": "market_analysis",
                "relevance_score": 10
            })

        return {
            "success": True,
            "query": field,
            "field": field,
            "insights": insights,
            "message": f"Found career insights for: {field}",
            "search_performed": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": field,
            "message": f"Error searching career insights: {str(e)}"
        }

# Tool definition for OpenAI function calling
get_career_insights_tool = {
    "type": "function",
    "function": {
        "name": "get_career_insights",
        "description": "Use this tool to provide career insights, job market trends, salary information, and growth opportunities for any career field. Perfect for when students ask about job prospects, career advice, or industry information.",
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "The career field or profession to research (e.g., 'AI engineering', 'software development', 'data science', 'web development', 'cybersecurity')"
                }
            },
            "required": ["field"]
        }
    }
}