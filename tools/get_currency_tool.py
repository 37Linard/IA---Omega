import requests


class GetCurrencyTool:
    name = "get_currency"
    description = (
        "Retorna cotação de moedas FIAT (dólar, euro, libra). "
        "NÃO use para Bitcoin/Ethereum/criptomoedas — use get_crypto para isso. "
        "Input: {'currency': 'BRL'} — código ISO: BRL, EUR, GBP, JPY, etc."
    )

    def run(self, input_data: dict) -> str:
        currency = input_data.get("currency", "BRL").upper().strip()

        if currency == "USD":
            return "Dica: 'USD' retorna 1.0 (sem utilidade). Para ver dólar em reais, use currency='BRL'."

        try:
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            rates = data.get("rates", {})
            date  = data.get("date", "desconhecida")

            if currency not in rates:
                available = [k for k in rates if len(k) == 3][:20]
                return f"Moeda '{currency}' não encontrada. Exemplos: {available}"

            rate = rates[currency]
            usd  = rates.get("USD", 1)

            return (
                f"Cotação em {date}:\n"
                f"1 USD = {rate} {currency}\n"
                f"1 {currency} = {round(usd/rate, 4)} USD"
            )

        except requests.Timeout:
            return "Erro: API de câmbio não respondeu em 10 segundos."
        except Exception as e:
            return f"Erro ao buscar cotação: {str(e)}"
