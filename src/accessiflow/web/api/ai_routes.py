"""AI configuration and suggestion API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from accessiflow.ai.registry import get_provider, available_providers
from accessiflow.remediation.ai_remediator import AIRemediator
from accessiflow.web.session import get_or_create_default_session, get_job
from accessiflow.web.models import (
    AIConfigRequest, AIConfigStatus,
    AISuggestionRequest, AISuggestionResponse,
)

router = APIRouter()


@router.post("/ai/config")
async def configure_ai(req: AIConfigRequest):
    session = get_or_create_default_session()
    try:
        provider = get_provider(req.provider, req.api_key, req.model or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    valid = await provider.validate_key()
    if not valid:
        return {"ok": False, "error": "API key validation failed"}

    session.ai_provider = req.provider
    session.ai_api_key = req.api_key
    session.ai_model = req.model or provider.model
    session.ai_validated = True
    return {"ok": True, "provider": req.provider, "model": session.ai_model}


@router.get("/ai/config/status")
async def ai_config_status():
    session = get_or_create_default_session()
    return AIConfigStatus(
        configured=bool(session.ai_provider and session.ai_api_key),
        provider=session.ai_provider,
        model=session.ai_model,
        validated=session.ai_validated,
    )


@router.get("/ai/providers")
async def list_providers():
    return available_providers()


@router.post("/ai/suggest/{job_id}")
async def suggest_fix(job_id: str, req: AISuggestionRequest):
    session = get_or_create_default_session()
    if not session.ai_validated:
        raise HTTPException(status_code=400, detail="AI provider not configured")

    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    all_issues = []
    for item in job.result.content_items:
        for issue in item.issues:
            all_issues.append(issue)
    for item in job.result.file_items:
        for issue in item.issues:
            all_issues.append(issue)

    if req.issue_index < 0 or req.issue_index >= len(all_issues):
        raise HTTPException(status_code=400, detail="Invalid issue index")

    issue = all_issues[req.issue_index]

    try:
        provider = get_provider(session.ai_provider, session.ai_api_key, session.ai_model)
        remediator = AIRemediator(provider)
        suggestion = await remediator.explain_issue(issue)
        return AISuggestionResponse(
            check_id=suggestion.issue_check_id,
            explanation=suggestion.explanation,
            suggested_fix=suggestion.suggested_fix,
            provider=suggestion.provider,
            model=suggestion.model,
        )
    except Exception as e:
        return AISuggestionResponse(error=str(e))


@router.post("/ai/suggest-batch/{job_id}")
async def suggest_batch(job_id: str):
    session = get_or_create_default_session()
    if not session.ai_validated:
        raise HTTPException(status_code=400, detail="AI provider not configured")

    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    ai_issues = []
    for item in job.result.content_items:
        for issue in item.issues:
            if issue.ai_fixable:
                ai_issues.append(issue)
    for item in job.result.file_items:
        for issue in item.issues:
            if issue.ai_fixable:
                ai_issues.append(issue)

    try:
        provider = get_provider(session.ai_provider, session.ai_api_key, session.ai_model)
        remediator = AIRemediator(provider)
        suggestions = []
        for issue in ai_issues:
            try:
                s = await remediator.explain_issue(issue)
                suggestions.append(AISuggestionResponse(
                    check_id=s.issue_check_id,
                    explanation=s.explanation,
                    suggested_fix=s.suggested_fix,
                    provider=s.provider,
                    model=s.model,
                ).model_dump())
            except Exception as e:
                suggestions.append(AISuggestionResponse(
                    check_id=issue.check_id, error=str(e)
                ).model_dump())
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
