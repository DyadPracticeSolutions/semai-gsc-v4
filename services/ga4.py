"""
SEMAI Analytics Intelligence Platform - Google Analytics 4 Service.

Pure-Python module for fetching and structuring GA4 data.
No Streamlit dependency.
"""

from __future__ import annotations

from googleapiclient.discovery import build


# =============================================================================
# Public API
# =============================================================================

def list_ga4_properties(creds) -> list[dict]:
    """Return all GA4 properties accessible with *creds*.

    Tries the ``google-analytics-admin`` package first, falling back to the
    REST API if the package is not installed.

    Args:
        creds: Google ``Credentials`` object with analytics scopes.

    Returns:
        List of dicts with keys ``property_id``, ``display_name``, and
        ``full_name``.
    """
    try:
        from google.analytics.admin import AnalyticsAdminServiceClient

        client = AnalyticsAdminServiceClient(credentials=creds)
        properties: list[dict] = []

        for account in client.list_accounts():
            account_name = account.name
            for prop in client.list_properties(
                request={"filter": f"parent:{account_name}"}
            ):
                properties.append(
                    {
                        "property_id": prop.name.split("/")[-1],
                        "display_name": prop.display_name,
                        "full_name": prop.name,
                    }
                )
        return properties

    except ImportError:
        pass  # Fall through to REST API

    # Fallback: REST API
    try:
        service = build("analyticsadmin", "v1beta", credentials=creds)
        accounts_response = service.accounts().list().execute()

        properties = []
        for account in accounts_response.get("accounts", []):
            props_response = (
                service.properties()
                .list(filter=f"parent:{account['name']}")
                .execute()
            )
            for prop in props_response.get("properties", []):
                properties.append(
                    {
                        "property_id": prop["name"].split("/")[-1],
                        "display_name": prop.get("displayName", prop["name"]),
                        "full_name": prop["name"],
                    }
                )
        return properties

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Internal helpers – native package variant
# ---------------------------------------------------------------------------

def _extract_ga4_native(creds, property_id: str, start_date, end_date) -> dict:
    """Fetch GA4 data using the ``google-analytics-data`` package."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        DateRange,
        Dimension,
        Metric,
    )

    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{property_id}"

    # 1) Summary metrics ------------------------------------------------
    summary_request = RunReportRequest(
        property=prop,
        date_ranges=[
            DateRange(start_date=str(start_date), end_date=str(end_date))
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
            Metric(name="screenPageViews"),
            Metric(name="conversions"),
            Metric(name="eventCount"),
        ],
    )
    summary_response = client.run_report(summary_request)

    summary_metrics: dict[str, float] = {}
    if summary_response.rows:
        row = summary_response.rows[0]
        metric_names = [
            "sessions",
            "totalUsers",
            "newUsers",
            "engagementRate",
            "averageSessionDuration",
            "bounceRate",
            "screenPageViews",
            "conversions",
            "eventCount",
        ]
        for i, metric in enumerate(row.metric_values):
            summary_metrics[metric_names[i]] = (
                float(metric.value) if metric.value else 0
            )

    # 2) Channel performance --------------------------------------------
    channel_request = RunReportRequest(
        property=prop,
        date_ranges=[
            DateRange(start_date=str(start_date), end_date=str(end_date))
        ],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="engagementRate"),
            Metric(name="conversions"),
        ],
        limit=20,
    )
    channel_response = client.run_report(channel_request)

    channels: list[dict] = []
    for row in channel_response.rows:
        channels.append(
            {
                "channel": row.dimension_values[0].value,
                "sessions": int(float(row.metric_values[0].value)),
                "users": int(float(row.metric_values[1].value)),
                "engagement_rate": round(
                    float(row.metric_values[2].value), 4
                ),
                "conversions": int(float(row.metric_values[3].value)),
            }
        )

    # 3) Top pages -------------------------------------------------------
    pages_request = RunReportRequest(
        property=prop,
        date_ranges=[
            DateRange(start_date=str(start_date), end_date=str(end_date))
        ],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="averageSessionDuration"),
        ],
        limit=20,
    )
    pages_response = client.run_report(pages_request)

    pages: list[dict] = []
    for row in pages_response.rows:
        pages.append(
            {
                "page": row.dimension_values[0].value,
                "pageviews": int(float(row.metric_values[0].value)),
                "sessions": int(float(row.metric_values[1].value)),
                "engagement_rate": round(
                    float(row.metric_values[2].value), 4
                ),
                "avg_session_duration": round(
                    float(row.metric_values[3].value), 2
                ),
            }
        )

    # 4) Device breakdown ------------------------------------------------
    device_request = RunReportRequest(
        property=prop,
        date_ranges=[
            DateRange(start_date=str(start_date), end_date=str(end_date))
        ],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="engagementRate"),
        ],
    )
    device_response = client.run_report(device_request)

    devices: list[dict] = []
    for row in device_response.rows:
        devices.append(
            {
                "device": row.dimension_values[0].value,
                "sessions": int(float(row.metric_values[0].value)),
                "users": int(float(row.metric_values[1].value)),
                "engagement_rate": round(
                    float(row.metric_values[2].value), 4
                ),
            }
        )

    return _build_ga4_payload(
        property_id, start_date, end_date,
        summary_metrics, channels, pages, devices,
    )


# ---------------------------------------------------------------------------
# Internal helpers – REST API fallback
# ---------------------------------------------------------------------------

def _extract_ga4_rest(creds, property_id: str, start_date, end_date) -> dict:
    """Fetch GA4 data using the REST API (no extra packages required)."""
    service = build("analyticsdata", "v1beta", credentials=creds)
    prop = f"properties/{property_id}"

    # 1) Summary metrics ------------------------------------------------
    summary_body = {
        "dateRanges": [
            {"startDate": str(start_date), "endDate": str(end_date)}
        ],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "newUsers"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
            {"name": "bounceRate"},
            {"name": "screenPageViews"},
            {"name": "conversions"},
            {"name": "eventCount"},
        ],
    }
    summary_resp = (
        service.properties().runReport(property=prop, body=summary_body).execute()
    )

    summary_metrics: dict[str, float] = {}
    if summary_resp.get("rows"):
        row = summary_resp["rows"][0]
        metric_names = [
            "sessions",
            "totalUsers",
            "newUsers",
            "engagementRate",
            "averageSessionDuration",
            "bounceRate",
            "screenPageViews",
            "conversions",
            "eventCount",
        ]
        for i, metric_val in enumerate(row.get("metricValues", [])):
            summary_metrics[metric_names[i]] = float(
                metric_val.get("value", 0)
            )

    # 2) Channel performance --------------------------------------------
    channel_body = {
        "dateRanges": [
            {"startDate": str(start_date), "endDate": str(end_date)}
        ],
        "dimensions": [{"name": "sessionDefaultChannelGroup"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "engagementRate"},
            {"name": "conversions"},
        ],
        "limit": 20,
    }
    channel_resp = (
        service.properties().runReport(property=prop, body=channel_body).execute()
    )

    channels: list[dict] = []
    for row in channel_resp.get("rows", []):
        channels.append(
            {
                "channel": row["dimensionValues"][0]["value"],
                "sessions": int(float(row["metricValues"][0]["value"])),
                "users": int(float(row["metricValues"][1]["value"])),
                "engagement_rate": round(
                    float(row["metricValues"][2]["value"]), 4
                ),
                "conversions": int(float(row["metricValues"][3]["value"])),
            }
        )

    # 3) Top pages -------------------------------------------------------
    pages_body = {
        "dateRanges": [
            {"startDate": str(start_date), "endDate": str(end_date)}
        ],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [
            {"name": "screenPageViews"},
            {"name": "sessions"},
            {"name": "engagementRate"},
            {"name": "averageSessionDuration"},
        ],
        "limit": 20,
    }
    pages_resp = (
        service.properties().runReport(property=prop, body=pages_body).execute()
    )

    pages: list[dict] = []
    for row in pages_resp.get("rows", []):
        pages.append(
            {
                "page": row["dimensionValues"][0]["value"],
                "pageviews": int(float(row["metricValues"][0]["value"])),
                "sessions": int(float(row["metricValues"][1]["value"])),
                "engagement_rate": round(
                    float(row["metricValues"][2]["value"]), 4
                ),
                "avg_session_duration": round(
                    float(row["metricValues"][3]["value"]), 2
                ),
            }
        )

    # 4) Device breakdown ------------------------------------------------
    device_body = {
        "dateRanges": [
            {"startDate": str(start_date), "endDate": str(end_date)}
        ],
        "dimensions": [{"name": "deviceCategory"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "totalUsers"},
            {"name": "engagementRate"},
        ],
    }
    device_resp = (
        service.properties().runReport(property=prop, body=device_body).execute()
    )

    devices: list[dict] = []
    for row in device_resp.get("rows", []):
        devices.append(
            {
                "device": row["dimensionValues"][0]["value"],
                "sessions": int(float(row["metricValues"][0]["value"])),
                "users": int(float(row["metricValues"][1]["value"])),
                "engagement_rate": round(
                    float(row["metricValues"][2]["value"]), 4
                ),
            }
        )

    return _build_ga4_payload(
        property_id, start_date, end_date,
        summary_metrics, channels, pages, devices,
    )


# ---------------------------------------------------------------------------
# Shared payload builder
# ---------------------------------------------------------------------------

def _build_ga4_payload(
    property_id: str,
    start_date,
    end_date,
    summary_metrics: dict,
    channels: list[dict],
    pages: list[dict],
    devices: list[dict],
) -> dict:
    """Assemble the final GA4 payload dictionary."""
    return {
        "property_id": property_id,
        "date_range": {"start": str(start_date), "end": str(end_date)},
        "summary_metrics": {
            "total_sessions": int(summary_metrics.get("sessions", 0)),
            "total_users": int(summary_metrics.get("totalUsers", 0)),
            "new_users": int(summary_metrics.get("newUsers", 0)),
            "engagement_rate": round(
                summary_metrics.get("engagementRate", 0), 4
            ),
            "avg_session_duration": round(
                summary_metrics.get("averageSessionDuration", 0), 2
            ),
            "bounce_rate": round(
                summary_metrics.get("bounceRate", 0), 4
            ),
            "total_pageviews": int(
                summary_metrics.get("screenPageViews", 0)
            ),
            "total_conversions": int(
                summary_metrics.get("conversions", 0)
            ),
            "total_events": int(summary_metrics.get("eventCount", 0)),
        },
        "channel_performance": sorted(
            channels, key=lambda x: x["sessions"], reverse=True
        ),
        "top_pages": sorted(
            pages, key=lambda x: x["pageviews"], reverse=True
        ),
        "device_breakdown": devices,
    }


# =============================================================================
# Main entry point
# =============================================================================

def extract_ga4_payload(
    creds,
    property_id: str,
    start_date,
    end_date,
) -> dict:
    """Extract and format GA4 data into a structured payload.

    Tries the native ``google-analytics-data`` package first and falls
    back to the REST API when the package is not installed.

    Args:
        creds: Google ``Credentials`` object.
        property_id: GA4 property ID (numeric string).
        start_date: Start date.
        end_date: End date.

    Returns:
        Structured dictionary with summary metrics, channels, pages, and
        device breakdown.  Contains an ``"error"`` key on failure.
    """
    try:
        return _extract_ga4_native(creds, property_id, start_date, end_date)
    except ImportError:
        pass
    except Exception as exc:
        # If native package is installed but request fails, return error
        return {"error": str(exc), "note": "Failed to fetch GA4 data."}

    try:
        return _extract_ga4_rest(creds, property_id, start_date, end_date)
    except Exception as exc:
        return {"error": str(exc), "note": "Failed to fetch GA4 data."}
