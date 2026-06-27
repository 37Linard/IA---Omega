import requests
from datetime import datetime


class GetCryptoTool:
    name = "get_crypto"
    description = (
        "Busca dados de criptomoeda: preço, variação, volume, RSI, médias móveis e Fear & Greed. "
        "Input: {'symbol': 'bitcoin', 'vs_currency': 'brl', 'days': 14}"
    )

    _COIN_MAP = {
        "btc": "bitcoin",      "bitcoin": "bitcoin",
        "eth": "ethereum",     "ethereum": "ethereum",
        "bnb": "binancecoin",  "binance": "binancecoin",
        "sol": "solana",       "solana": "solana",
        "ada": "cardano",      "cardano": "cardano",
        "xrp": "ripple",       "ripple": "ripple",
        "doge": "dogecoin",    "dogecoin": "dogecoin",
        "dot": "polkadot",     "avax": "avalanche-2",
        "matic": "matic-network", "link": "chainlink",
    }

    def run(self, params: dict) -> str:
        # aceita 'symbol', 'currency' ou 'coin' como chave
        symbol   = (params.get("symbol") or params.get("currency") or params.get("coin") or "bitcoin").lower().strip()
        vs       = (params.get("vs_currency") or params.get("vs") or "brl").lower()
        days     = max(7, int(params.get("days", 14)))
        coin_id  = self._COIN_MAP.get(symbol, symbol)

        try:
            # Dados atuais
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                params={"localization": "false", "tickers": "false",
                        "community_data": "false", "developer_data": "false"},
                timeout=10,
            )
            r.raise_for_status()
            d  = r.json()
            mk = d.get("market_data", {})

            price      = mk.get("current_price", {}).get(vs, 0)
            change_24h = mk.get("price_change_percentage_24h", 0) or 0
            change_7d  = mk.get("price_change_percentage_7d", 0) or 0
            volume     = mk.get("total_volume", {}).get(vs, 0)
            mktcap     = mk.get("market_cap", {}).get(vs, 0)
            high_24h   = mk.get("high_24h", {}).get(vs, 0)
            low_24h    = mk.get("low_24h", {}).get(vs, 0)

            # Histórico para indicadores
            rh = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                params={"vs_currency": vs, "days": days, "interval": "daily"},
                timeout=10,
            )
            rh.raise_for_status()
            prices = [p[1] for p in rh.json().get("prices", [])]

            rsi  = self._rsi(prices)
            ma7  = round(sum(prices[-7:])  / 7,  2) if len(prices) >= 7  else None
            ma14 = round(sum(prices[-14:]) / 14, 2) if len(prices) >= 14 else None
            fg   = self._fear_greed()

            VS = vs.upper()
            lines = [
                f"=== {d.get('name', coin_id).upper()} ({d.get('symbol','').upper()}) ===",
                f"Preço atual : {VS} {price:,.2f}",
                f"Variação 24h: {change_24h:+.2f}%  |  7d: {change_7d:+.2f}%",
                f"Máx/Mín 24h : {VS} {high_24h:,.2f} / {VS} {low_24h:,.2f}",
                f"Volume 24h  : {VS} {volume:,.0f}",
                f"Market Cap  : {VS} {mktcap:,.0f}",
                "",
                "=== INDICADORES TÉCNICOS ===",
            ]

            if rsi is not None:
                sig = "SOBRECOMPRADO ⚠️" if rsi > 70 else ("SOBREVENDIDO ⚠️" if rsi < 30 else "NEUTRO ✅")
                lines.append(f"RSI ({days}d)  : {rsi:.1f} — {sig}")

            if ma7:
                t7 = "↑ preço acima" if price > ma7 else "↓ preço abaixo"
                lines.append(f"MA7          : {VS} {ma7:,.2f}  ({t7})")
            if ma14:
                t14 = "↑ preço acima" if price > ma14 else "↓ preço abaixo"
                lines.append(f"MA14         : {VS} {ma14:,.2f}  ({t14})")

            if fg:
                lines.append(f"Fear & Greed : {fg['value']}/100 — {fg['label']}")

            lines.append(f"\nFonte: CoinGecko | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            return "\n".join(lines)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f"Erro: moeda '{symbol}' não encontrada. Use nome completo: 'bitcoin', 'ethereum', etc."
            return f"Erro HTTP: {e}"
        except Exception as e:
            return f"Erro: {e}"

    def _rsi(self, prices: list, period: int = 14):
        if len(prices) < period + 1:
            return None
        deltas = [prices[i+1] - prices[i] for i in range(len(prices) - 1)]
        gains  = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        if not gains and not losses:
            return 50.0
        avg_gain = sum(gains[-period:])  / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)

    def _fear_greed(self):
        try:
            r = requests.get("https://api.alternative.me/fng/", timeout=5)
            d = r.json()["data"][0]
            return {"value": int(d["value"]), "label": d["value_classification"]}
        except Exception:
            return None
