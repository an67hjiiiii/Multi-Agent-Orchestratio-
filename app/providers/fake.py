from __future__ import annotations
import asyncio
import json
import re
import uuid
from app.core.types import ProviderResult, Usage
from app.providers.base import Provider

class FakeProvider(Provider):
    name = "fake"
    model = "fake-s0-v2"

    async def generate(self, *, system: str, user: str) -> ProviderResult:
        await asyncio.sleep(0.01)
        marker = system.upper()
        if "TASK_DECOMPOSER" in marker:
            text = json.dumps({"tasks": self._tasks(user)}, ensure_ascii=False)
        elif "VANILLA_RAG_ANSWERER" in marker:
            evidence = self._extract_section(user, "EVIDENCE:")
            citations = self._chunk_ids(evidence)
            if not citations:
                text = json.dumps({"status":"NO_EVIDENCE","answer":"Chưa đủ evidence để kết luận.","citations":[],"missing_information":["relevant evidence"]}, ensure_ascii=False)
            else:
                text = json.dumps({"status":"COMPLETE","answer":"Câu trả lời demo source-grounded từ Vanilla RAG.","citations":citations[:2],"missing_information":[]}, ensure_ascii=False)
        elif "WORKER" in marker:
            domain = self._extract(user, "DOMAIN", "general")
            evidence = self._extract(user, "EVIDENCE", "")
            citations = self._chunk_ids(evidence)
            if not evidence.strip() or not citations:
                text = json.dumps({"status":"NO_EVIDENCE","answer":"Chưa đủ evidence để kết luận.","citations":[],"missing_information":["relevant evidence"]}, ensure_ascii=False)
            else:
                text = json.dumps({"status":"COMPLETE","answer":f"[{domain}] Kết luận demo dựa trên evidence được cung cấp.","citations":citations[:2],"missing_information":[]}, ensure_ascii=False)
        elif "SYNTHESIZER" in marker:
            citations = self._chunk_ids(user)
            suffix = (" Nguồn: " + ", ".join(f"[{c}]" for c in citations[:4])) if citations else ""
            text = "Bản tổng hợp demo đã kết hợp các kết quả task và giữ citation theo evidence ID." + suffix
        else:
            text = "Câu trả lời demo source-grounded từ pipeline local."
        usage = Usage(max(1, len(user)//4), max(1, len(text)//4))
        return ProviderResult(text=text, usage=usage, request_id="fake_"+uuid.uuid4().hex[:10], model=self.model)

    def _tasks(self, user: str) -> list[dict]:
        low = user.lower()
        tasks: list[dict] = []
        if any(x in low for x in ["security", "auth", "jwt", "đăng nhập", "phân quyền", "authorization"]):
            tasks.append({"id":"T1","goal":"Review authentication and authorization requirements","domain":"security","depends_on":[],"evidence_needs":["authentication","authorization","JWT"]})
        if any(x in low for x in ["database", "sql", "query", "dữ liệu", "truy vấn"]):
            tasks.append({"id":f"T{len(tasks)+1}","goal":"Review database and query concerns","domain":"database","depends_on":[],"evidence_needs":["database","query"]})
        if any(x in low for x in ["api", "architecture", "kiến trúc", "endpoint"]):
            tasks.append({"id":f"T{len(tasks)+1}","goal":"Review API and architecture concerns","domain":"api_architecture","depends_on":[],"evidence_needs":["API","architecture"]})
        if not tasks:
            tasks.append({"id":"T1","goal":"Answer the user's request from available evidence","domain":"api_architecture","depends_on":[],"evidence_needs":["user request"]})
        return tasks

    @staticmethod
    def _extract(text: str, key: str, default: str) -> str:
        m = re.search(rf"\[{key}\](.*?)\[/{key}\]", text, re.S | re.I)
        return m.group(1).strip() if m else default

    @staticmethod
    def _extract_section(text: str, heading: str) -> str:
        idx = text.find(heading)
        return text[idx + len(heading):] if idx >= 0 else ""

    @staticmethod
    def _chunk_ids(text: str) -> list[str]:
        found = re.findall(r"\[(src_[0-9a-f]{16}_c\d{4})\]", text)
        return list(dict.fromkeys(found))
