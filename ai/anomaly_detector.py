from sqlalchemy        import create_engine, text
from langchain_openai  import ChatOpenAI
from langchain_groq import ChatGroq
import pandas          as pd
from datetime          import datetime, timedelta
from typing            import List, Dict
import json
from config            import settings


class AnomalyDetector:
    def __init__(self):
       
        # self.llm = ChatOpenAI(
        #     api_key     = settings.OPENAI_API_KEY,
        #     model       = "gpt-4o-mini",
        #     temperature = 0.3    
        # )
        
        self.llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0.3
        )

    def calculate_percentage_change(
        self,
        current  : float,
        previous : float
    ) -> float:
        """
        Calculate % change between two values.
        Formula: ((current - previous) / previous) * 100
        """
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100

    def get_kpi_value(
        self,
        connection_url : str,
        query          : str
    ) -> float:
        try:
            engine = create_engine(connection_url)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                row    = result.fetchone()
                value  = float(row[0]) if row and row[0] else 0.0
            engine.dispose()
            return value
        except Exception as e:
            print(f"KPI query error: {e}")
            return 0.0

    def explain_anomaly(
        self,
        kpi_name       : str,
        current_value  : float,
        previous_value : float,
        pct_change     : float
    ) -> Dict:
        direction = "increased" if pct_change > 0 else "decreased"
        abs_pct   = abs(pct_change)

        if abs_pct >= 50:
            severity = "CRITICAL"
        elif abs_pct >= 30:
            severity = "HIGH"
        elif abs_pct >= 15:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        prompt = f"""You are a business analyst detecting data anomalies.

KPI: {kpi_name}
Current Value: {current_value:,.2f}
Previous Value: {previous_value:,.2f}
Change: {direction} by {abs_pct:.1f}%
Severity: {severity}

Provide a JSON response with exactly these fields:
{{
    "message": "one sentence describing what happened",
    "possible_causes": ["cause 1", "cause 2", "cause 3"],
    "recommended_action": "one sentence on what to do",
    "severity": "{severity}"
}}

Only respond with valid JSON. No other text."""

        try:
            response    = self.llm.invoke(prompt)
            explanation = json.loads(response.content)
            return explanation
        except:
            return {
                "message"            : f"{kpi_name} {direction} by {abs_pct:.1f}%",
                "possible_causes"    : ["Data fluctuation", "Seasonal pattern", "External factor"],
                "recommended_action" : "Review recent transactions and team activities",
                "severity"           : severity
            }

    def detect_anomalies(
        self,
        company_id     : int,
        connection_url : str,
        kpi_configs    : List[Dict]
    ) -> List[Dict]:
        alerts = []

        for kpi in kpi_configs:
            print(f"🔍 Checking KPI: {kpi['name']}")

            current = self.get_kpi_value(
                connection_url,
                kpi["current_query"]
            )

            historical = self.get_kpi_value(
                connection_url,
                kpi["historical_query"]
            )

            # Percentage change
            pct_change = self.calculate_percentage_change(current, historical)

            print(f"   Current: {current:,.2f} | Historical avg: {historical:,.2f} | Change: {pct_change:.1f}%")

            # Check if change exceeds threshold
            threshold = kpi.get("threshold_pct", 20)

            if abs(pct_change) >= threshold:
                print(f" ANOMALY DETECTED! Change {pct_change:.1f}% exceeds threshold {threshold}%")

                #  AI explanation
                explanation = self.explain_anomaly(
                    kpi_name       = kpi["name"],
                    current_value  = current,
                    previous_value = historical,
                    pct_change     = pct_change
                )

                # Alert object
                alert = {
                    "company_id"      : company_id,
                    "kpi_name"        : kpi["name"],
                    "current_value"   : current,
                    "historical_value": historical,
                    "pct_change"      : round(pct_change, 2),
                    "severity"        : explanation["severity"],
                    "message"         : explanation["message"],
                    "possible_causes" : explanation["possible_causes"],
                    "recommended_action": explanation["recommended_action"],
                    "detected_at"     : datetime.utcnow().isoformat()
                }

                alerts.append(alert)

        return alerts


DEFAULT_KPI_CONFIGS = [
    {
        "name"            : "Daily Revenue",
        "current_query"   : """
            SELECT COALESCE(SUM(amount), 0)
            FROM orders
            WHERE DATE(created_at) = CURDATE()
        """,
        "historical_query": """
            SELECT COALESCE(AVG(daily_rev), 0) FROM (
                SELECT DATE(created_at) as dt,
                       SUM(amount) as daily_rev
                FROM orders
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND DATE(created_at) != CURDATE()
                GROUP BY DATE(created_at)
            ) t
        """,
        "threshold_pct": 20
    },
    {
        "name"            : "Order Count",
        "current_query"   : """
            SELECT COALESCE(COUNT(*), 0)
            FROM orders
            WHERE DATE(created_at) = CURDATE()
        """,
        "historical_query": """
            SELECT COALESCE(AVG(daily_count), 0) FROM (
                SELECT DATE(created_at) as dt,
                       COUNT(*) as daily_count
                FROM orders
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND DATE(created_at) != CURDATE()
                GROUP BY DATE(created_at)
            ) t
        """,
        "threshold_pct": 25
    },
    {
        "name"            : "New Customers",
        "current_query"   : """
            SELECT COALESCE(COUNT(*), 0)
            FROM customers
            WHERE DATE(created_at) = CURDATE()
        """,
        "historical_query": """
            SELECT COALESCE(AVG(daily_new), 0) FROM (
                SELECT DATE(created_at) as dt,
                       COUNT(*) as daily_new
                FROM customers
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                  AND DATE(created_at) != CURDATE()
                GROUP BY DATE(created_at)
            ) t
        """,
        "threshold_pct": 30
    }
]