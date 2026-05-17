import urllib.parse

def generate_vietqr_url(
    bank_id: str,
    account_no: str,
    amount: int,
    account_name: str | None = None,
    description: str | None = None,
    template: str = "compact2"
) -> str:
    """
    Generate a VietQR URL for payment.
    Format: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<DESCRIPTION>&accountName=<ACCOUNT_NAME>
    """
    base_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png"
    
    params = {}
    if amount > 0:
        params["amount"] = amount
    if description:
        params["addInfo"] = description
    if account_name:
        params["accountName"] = account_name
        
    if params:
        query_string = urllib.parse.urlencode(params)
        return f"{base_url}?{query_string}"
    
    return base_url
