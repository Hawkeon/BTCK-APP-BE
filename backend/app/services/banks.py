import httpx
from typing import Any

class BankService:
    def __init__(self):
        self.base_url = "https://api.vietqr.io/v2/banks"
        self._banks_cache: list[dict[str, Any]] | None = None

    async def get_all_banks(self) -> list[dict[str, Any]]:
        """Fetch and cache the list of banks from VietQR."""
        if self._banks_cache:
            return self._banks_cache
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url)
                response.raise_for_status()
                data = response.json()
                if data.get("code") == "00":
                    self._banks_cache = data.get("data", [])
                    return self._banks_cache
                return []
            except Exception:
                return []

    async def is_valid_bank(self, bank_code: str) -> bool:
        """Check if a bank code is valid (case-insensitive)."""
        banks = await self.get_all_banks()
        # Check both shortName and code (case-insensitive)
        valid_codes = {b.get("shortName", "").upper() for b in banks} | \
                      {b.get("code", "").upper() for b in banks}
        return bank_code.upper() in valid_codes

bank_service = BankService()
