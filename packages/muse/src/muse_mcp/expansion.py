"""Prompt expansion for Muse MCP.

Converts raw prompts into rich working objects with goals, domains,
constraints, and desired outputs.
"""

from __future__ import annotations

import re
from typing import Any

from .database import Database
from .models import WorkingObject, Fragment


# Domain keywords for automatic detection
DOMAIN_KEYWORDS = {
    "agent memory": ["memory", "remember", "recall", "store", "retrieve", "forget"],
    "RAG": ["retrieval", "rag", "embedding", "vector", "search", "semantic"],
    "creativity": ["creative", "generate", "novel", "idea", "brainstorm", "innovate"],
    "knowledge graphs": ["graph", "node", "edge", "relationship", "ontology", "schema"],
    "machine learning": ["ml", "model", "train", "neural", "learning", "ai"],
    "software architecture": ["architecture", "design", "pattern", "module", "component"],
    "databases": ["database", "sql", "nosql", "query", "storage", "persistence"],
    "api design": ["api", "endpoint", "rest", "graphql", "interface"],
    "user experience": ["ux", "user", "interface", "experience", "usability"],
    "security": ["security", "auth", "encryption", "permission", "access"],
    "performance": ["performance", "optimize", "speed", "latency", "throughput"],
    "testing": ["test", "unit", "integration", "coverage", "quality"],
}

# Constraint indicators
CONSTRAINT_PATTERNS = [
    r"must (?:be|have|support|use|include) (.+?)(?:\.|,|$)",
    r"should (?:be|have|support|use|include) (.+?)(?:\.|,|$)",
    r"need[s]? to (?:be|have|support) (.+?)(?:\.|,|$)",
    r"require[s]? (.+?)(?:\.|,|$)",
    r"(?:local-first|offline|self-hosted|private)",
    r"(?:fast|quick|responsive|low-latency)",
    r"(?:simple|minimal|lightweight)",
    r"(?:scalable|distributed)",
    r"compatible with (.+?)(?:\.|,|$)",
]

# Output indicators
OUTPUT_PATTERNS = [
    r"(?:want|need|looking for) (?:a |an )?(.+?)(?:\.|,|$)",
    r"output[s]?: (.+?)(?:\.|,|$)",
    r"deliverable[s]?: (.+?)(?:\.|,|$)",
    r"produce (?:a |an )?(.+?)(?:\.|,|$)",
    r"create (?:a |an )?(.+?)(?:\.|,|$)",
    r"build (?:a |an )?(.+?)(?:\.|,|$)",
]


class PromptExpander:
    """Expands raw prompts into rich working objects."""

    def __init__(self, db: Database):
        """Initialize prompt expander.

        Args:
            db: Database instance
        """
        self.db = db

    def expand(
        self,
        user_id: str,
        raw_prompt: str,
        context: dict[str, Any] | None = None,
    ) -> WorkingObject:
        """Expand a raw prompt into a structured working object.

        Args:
            user_id: User ID
            raw_prompt: The raw prompt text
            context: Optional additional context

        Returns:
            Expanded WorkingObject
        """
        prompt_lower = raw_prompt.lower()

        # Extract goal
        goal = self._extract_goal(raw_prompt)

        # Detect domains
        domains = self._detect_domains(prompt_lower)

        # Extract constraints
        constraints = self._extract_constraints(raw_prompt)

        # Extract desired outputs
        desired_outputs = self._extract_outputs(raw_prompt)

        # Add context-provided info
        if context:
            if "domains" in context:
                domains.extend(context["domains"])
                domains = list(set(domains))
            if "constraints" in context:
                constraints.extend(context["constraints"])
            if "desired_outputs" in context:
                desired_outputs.extend(context["desired_outputs"])

        # Create working object
        wo = WorkingObject(
            user_id=user_id,
            raw_prompt=raw_prompt,
            goal=goal,
            domains=domains,
            constraints=constraints,
            desired_outputs=desired_outputs,
        )

        # Store in database
        self.db.insert_working_object(wo)

        return wo

    def _extract_goal(self, prompt: str) -> str:
        """Extract the main goal from the prompt."""
        # Look for explicit goal statements
        goal_patterns = [
            r"(?:goal|objective|aim)[:\s]+(.+?)(?:\.|$)",
            r"(?:i want to|we need to|trying to) (.+?)(?:\.|$)",
            r"(?:help me|help us) (.+?)(?:\.|$)",
        ]

        for pattern in goal_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fall back to first sentence or phrase
        sentences = re.split(r'[.!?]', prompt)
        if sentences:
            return sentences[0].strip()

        return prompt[:200].strip()

    def _detect_domains(self, prompt_lower: str) -> list[str]:
        """Detect relevant domains from the prompt."""
        detected = []

        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in prompt_lower for kw in keywords):
                detected.append(domain)

        return detected

    def _extract_constraints(self, prompt: str) -> list[str]:
        """Extract constraints from the prompt."""
        constraints = []

        for pattern in CONSTRAINT_PATTERNS:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match) > 3:
                    constraints.append(match.strip())

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for c in constraints:
            c_lower = c.lower()
            if c_lower not in seen:
                seen.add(c_lower)
                unique.append(c)

        return unique

    def _extract_outputs(self, prompt: str) -> list[str]:
        """Extract desired outputs from the prompt."""
        outputs = []

        for pattern in OUTPUT_PATTERNS:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and len(match) > 3:
                    outputs.append(match.strip())

        # Deduplicate
        seen = set()
        unique = []
        for o in outputs:
            o_lower = o.lower()
            if o_lower not in seen:
                seen.add(o_lower)
                unique.append(o)

        return unique

    def enrich_from_mind(
        self,
        wo: WorkingObject,
        memories: list[dict[str, Any]],
        patterns: list[str] | None = None,
        failures: list[str] | None = None,
    ) -> WorkingObject:
        """Enrich working object with Mind MCP retrieval results.

        Args:
            wo: Working object to enrich
            memories: Retrieved memories from Mind MCP
            patterns: Identified patterns
            failures: Past failures

        Returns:
            Enriched working object
        """
        # Extract memory IDs
        wo.relevant_memories = [m.get("id", m.get("memory_id", "")) for m in memories]

        if patterns:
            wo.relevant_patterns = patterns

        if failures:
            wo.relevant_failures = failures

        return wo

    def to_response(self, wo: WorkingObject) -> dict[str, Any]:
        """Convert working object to API response format."""
        return {
            "id": wo.id,
            "user_id": wo.user_id,
            "raw_prompt": wo.raw_prompt,
            "expanded": {
                "goal": wo.goal,
                "domains": wo.domains,
                "constraints": wo.constraints,
                "desired_outputs": wo.desired_outputs,
            },
            "context": {
                "relevant_memories": wo.relevant_memories,
                "relevant_patterns": wo.relevant_patterns,
                "relevant_failures": wo.relevant_failures,
            },
            "fragment_ids": wo.fragment_ids,
            "created_at": wo.created_at.isoformat(),
            "expires_at": wo.expires_at.isoformat() if wo.expires_at else None,
        }
