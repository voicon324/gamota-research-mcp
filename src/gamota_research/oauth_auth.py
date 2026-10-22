from __future__ import annotations

from typing import Any

from mcp.server.auth.provider import AccessToken
from mcp.types import CallToolResult, TextContent


_TOOL_SCOPES = {
    "create_research_run": "research:write",
    "set_research_contract": "research:write",
    "update_research_progress": "research:write",
    "save_research_source": "research:write",
    "save_research_evidence": "research:write",
    "save_research_claim": "research:write",
    "record_research_issue": "research:write",
    "finalize_research_run": "research:write",
    "get_research_run": "research:read",
    "get_claim_trace": "research:read",
    "get_claim_lineage_audit": "research:read",
    "publish_game_decision_brief": "report:publish",
    "list_published_reports": "research:read",
    "get_published_report": "research:read",
    "search_store_apps": "research:write",
    "get_game_details": "research:write",
    "get_store_chart_snapshot": "research:write",
    "get_store_chart_history": "research:read",
}


class CompositeTokenVerifier:
    """Preserve the legacy shared bearer while accepting separately issued OAuth tokens."""

    def __init__(self, legacy_token: str, oauth_verifier: Any, resource_url: str) -> None:
        self.legacy_token = legacy_token
        self.oauth_verifier = oauth_verifier
        self.resource_url = resource_url

    async def verify_token(self, token: str) -> AccessToken | None:
        import secrets

        if secrets.compare_digest(token, self.legacy_token):
            return AccessToken(
                token=token,
                client_id="gamota-mission2",
                scopes=["gamota:research"],
                resource=self.resource_url,
                subject="legacy-owner",
            )
        return await self.oauth_verifier.verify_token(token)


class ToolScopeMiddleware:
    """Attach ChatGPT OAuth scheme metadata and enforce the scope per tool call."""

    def __init__(self, resource_metadata_url: str) -> None:
        self.resource_metadata_url = resource_metadata_url

    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        if ctx.method == "tools/list":
            result = await call_next(ctx)
            if hasattr(result, "model_dump"):
                payload = result.model_dump(mode="json", by_alias=True)
            else:
                payload = dict(result)
            for tool in payload.get("tools", []):
                required_scope = _TOOL_SCOPES.get(tool.get("name"))
                if required_scope is None:
                    continue
                tool["securitySchemes"] = [
                    {"type": "oauth2", "scopes": [required_scope]}
                ]
            return payload

        if ctx.method != "tools/call":
            return await call_next(ctx)

        tool_name = (ctx.params or {}).get("name")
        required_scope = _TOOL_SCOPES.get(tool_name)
        request = ctx.request
        user = request.scope.get("user") if request is not None else None
        access_token = getattr(user, "access_token", None)
        granted_scopes = set(getattr(access_token, "scopes", []))
        legacy_full_access = "gamota:research" in granted_scopes
        if required_scope is None or (required_scope not in granted_scopes and not legacy_full_access):
            scope_label = required_scope or "an explicitly mapped permission"
            challenge = (
                f'Bearer resource_metadata="{self.resource_metadata_url}", '
                'error="insufficient_scope", '
                f'error_description="This tool requires {scope_label}"'
            )
            return CallToolResult(
                content=[TextContent(text=f"Insufficient permission: {scope_label}.")],
                isError=True,
                _meta={"mcp/www_authenticate": [challenge]},
            )
        return await call_next(ctx)
