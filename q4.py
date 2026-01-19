#!/usr/bin/env python3
"""
AWS Cost and Usage Report (CUR) Analysis Script

This script analyzes a CUR parquet export to answer various cost and usage questions.
"""

import sys

import pandas as pd


def load_cur_data(file_path):
    """Load CUR data from parquet file"""
    try:
        df = pd.read_parquet(file_path)
        print(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        sys.exit(1)


def analyze_highest_cost_day(df):
    """Find the highest-cost day and top service contributor"""
    print("\n=== HIGHEST COST DAY ANALYSIS ===")

    # Group by date and calculate total cost per day
    daily_service_cost = (
        df.groupby(["usage_date", "line_item_product_code"])["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )

    # Find highest cost day
    daily_total = (
        df.groupby("usage_date")["line_item_unblended_cost"].sum().reset_index()
    )
    highest_cost_day = daily_total.loc[
        daily_total["line_item_unblended_cost"].idxmax(), "usage_date"
    ]
    highest_cost_day_str = highest_cost_day.strftime("%Y-%m-%d")

    # Top service on highest cost day
    top_service_day = (
        daily_service_cost[daily_service_cost["usage_date"] == highest_cost_day]
        .nlargest(1, "line_item_unblended_cost")["line_item_product_code"]
        .values[0]
    )

    # Average service cost across all days
    avg_service_cost = (
        df.groupby("line_item_product_code")["line_item_unblended_cost"].sum()
        / df["usage_date"].nunique()
    )
    top_service_avg = avg_service_cost.idxmax()

    # Results
    same_service = top_service_day == top_service_avg

    print(f"highest_cost_day = {highest_cost_day_str}")
    print(f"top_service_that_day = {top_service_day}")
    print(f"top_service_avg = {top_service_avg}")
    print(f"same_service = {str(same_service).lower()}")

    return {
        "highest_cost_day": highest_cost_day,
        "top_service_that_day": top_service_day,
        "top_service_avg": top_service_avg,
        "same_service": same_service,
    }


def analyze_missing_resource_ids(df):
    """Find services with highest percentage of missing resource IDs"""
    print("\n=== MISSING RESOURCE ID ANALYSIS ===")

    # Group by service and calculate null resource ID percentages
    service_stats = (
        df.groupby("line_item_product_code")
        .agg(
            {
                "line_item_resource_id": lambda x: x.isnull().sum(),
                "line_item_unblended_cost": "count",  # Total records per service
            }
        )
        .reset_index()
    )

    service_stats.columns = ["service", "null_resource_ids", "total_records"]
    service_stats["null_resource_id_pct"] = (
        service_stats["null_resource_ids"] / service_stats["total_records"] * 100
    ).round(1)

    # Filter to services with significant usage (more than 100 records)
    service_stats = service_stats[service_stats["total_records"] > 100]
    service_stats = service_stats.sort_values("null_resource_id_pct", ascending=False)

    print("service | null_resource_id_pct")
    print("--------------------------------")

    # Return only services with the highest percentage of missing resource IDs
    max_pct = service_stats["null_resource_id_pct"].max()
    highest_services = service_stats[service_stats["null_resource_id_pct"] == max_pct]
    return highest_services.set_index("service")["null_resource_id_pct"].to_dict()


def analyze_dataset_structure(df):
    """Analyze what the dataset represents - dimensions and measures"""
    print("\n=== DATASET STRUCTURE ANALYSIS ===")

    print("This dataset represents AWS Cost and Usage Report (CUR) data.")
    print("\nDIMENSIONS (categorical attributes for grouping/filtering):")
    dimensions = [
        "usage_date - Date when the usage occurred",
        "line_item_usage_account_id - AWS account ID",
        "line_item_usage_account_name - AWS account name",
        "product_region_code - AWS region (e.g., us-east-1)",
        "line_item_product_code - AWS service code (e.g., EC2, S3, RDS)",
        "product_product_family - Product family category",
        "line_item_usage_type - Specific usage type (e.g., BoxUsage:c5.large)",
        "line_item_operation - AWS operation/API call",
        "line_item_resource_id - Unique resource identifier",
        "pricing_unit - Unit of measurement for pricing (e.g., Hrs, GB)",
    ]

    for dim in dimensions:
        print(f"- {dim}")

    print("\nMEASURES (quantitative values that can be aggregated):")
    measures = [
        "line_item_unblended_cost - Actual cost in USD (unblended)",
        "line_item_usage_amount - Quantity of usage consumed",
    ]

    for measure in measures:
        print(f"- {measure}")


def analyze_top_spending_services(df):
    """Analyze which services have the most spending"""
    print("\n=== TOP SPENDING SERVICES ANALYSIS ===")

    service_costs = (
        df.groupby("line_item_product_code")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    service_costs = service_costs.sort_values(
        "line_item_unblended_cost", ascending=False
    )
    total_cost = service_costs["line_item_unblended_cost"].sum()

    service_costs["percentage"] = (
        service_costs["line_item_unblended_cost"] / total_cost * 100
    ).round(2)

    print("Top 10 services by total spending:")
    print("Service     | Total Cost ($) | Percentage")
    print("------------------------------------------")

    # Return top 10 as a dict with service as key and cost as value
    return (
        service_costs.head(10)
        .set_index("line_item_product_code")["line_item_unblended_cost"]
        .to_dict()
    )


def analyze_cost_concentration(df):
    """Analyze what percentage of total cost comes from top 10% of resources/services"""
    print("\n=== COST CONCENTRATION ANALYSIS ===")

    # Analysis by resources
    resource_costs = (
        df.groupby("line_item_resource_id")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    resource_costs = resource_costs.dropna()  # Remove null resource IDs
    resource_costs = resource_costs.sort_values(
        "line_item_unblended_cost", ascending=False
    )

    total_cost = resource_costs["line_item_unblended_cost"].sum()
    top_10pct_resources = int(len(resource_costs) * 0.1)
    top_resources_cost = resource_costs.head(top_10pct_resources)[
        "line_item_unblended_cost"
    ].sum()
    resource_concentration = (top_resources_cost / total_cost * 100).round(2)

    # Analysis by services
    service_costs = (
        df.groupby("line_item_product_code")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    service_costs = service_costs.sort_values(
        "line_item_unblended_cost", ascending=False
    )

    total_cost_services = service_costs["line_item_unblended_cost"].sum()
    top_10pct_services = int(len(service_costs) * 0.1)
    top_services_cost = service_costs.head(top_10pct_services)[
        "line_item_unblended_cost"
    ].sum()
    service_concentration = (top_services_cost / total_cost_services * 100).round(2)

    return {
        "resource_concentration": resource_concentration,
        "service_concentration": service_concentration,
    }


def analyze_service_deep_dive(df, service_code):
    """Deep dive analysis of a specific service"""
    print(f"\n=== {service_code} DEEP DIVE ANALYSIS ===")

    # Filter data for the specific service
    service_data = df[df["line_item_product_code"] == service_code].copy()

    if len(service_data) == 0:
        print(f"No data found for service {service_code}")
        return

    # Cost by day (top 5 days)
    print("\nTop 5 costliest days:")
    daily_costs = (
        service_data.groupby("usage_date")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    daily_costs = daily_costs.sort_values("line_item_unblended_cost", ascending=False)
    top_days_dict = (
        daily_costs.head(5)
        .set_index("usage_date")["line_item_unblended_cost"]
        .to_dict()
    )
    print(top_days_dict)

    # Cost by usage type (top 5)
    print("\nTop 5 usage types by cost:")
    usage_type_costs = (
        service_data.groupby("line_item_usage_type")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    usage_type_costs = usage_type_costs.sort_values(
        "line_item_unblended_cost", ascending=False
    )
    top_usage_types_dict = (
        usage_type_costs.head(5)
        .set_index("line_item_usage_type")["line_item_unblended_cost"]
        .to_dict()
    )
    print(top_usage_types_dict)

    # Cost by resource (top 10 resources)
    print("\nTop 10 resources by cost:")
    resource_costs = (
        service_data.groupby("line_item_resource_id")["line_item_unblended_cost"]
        .sum()
        .reset_index()
    )
    resource_costs = resource_costs.dropna()  # Remove null resource IDs
    resource_costs = resource_costs.sort_values(
        "line_item_unblended_cost", ascending=False
    )
    top_resources_dict = (
        resource_costs.head(10)
        .set_index("line_item_resource_id")["line_item_unblended_cost"]
        .to_dict()
    )
    print(top_resources_dict)
    total_resource_cost = resource_costs["line_item_unblended_cost"].sum()

    # Cost concentration analysis
    if len(resource_costs) > 0:
        top_10pct = int(len(resource_costs) * 0.1)
        if top_10pct > 0:
            top_resources_cost = resource_costs.head(top_10pct)[
                "line_item_unblended_cost"
            ].sum()
            concentration_pct = (top_resources_cost / total_resource_cost * 100).round(
                2
            )

            if concentration_pct > 80:
                concentration_desc = "highly concentrated"
            elif concentration_pct > 60:
                concentration_desc = "moderately concentrated"
            else:
                concentration_desc = "spread out"

            print(
                f"This indicates the service's cost is {concentration_desc} among its resources."
            )


def analyze_time_patterns(df):
    """Analyze time-based patterns in cost data"""
    print("\n=== TIME PATTERN ANALYSIS ===")

    # Aggregate costs by day
    daily_costs = (
        df.groupby("usage_date")["line_item_unblended_cost"]
        .sum()
        .reset_index()
        .sort_values("usage_date")
    )

    # Add day of week information
    daily_costs["day_of_week"] = daily_costs["usage_date"].dt.dayofweek
    daily_costs["day_name"] = daily_costs["usage_date"].dt.day_name()
    daily_costs["is_weekend"] = daily_costs["day_of_week"].isin(
        [5, 6]
    )  # Saturday=5, Sunday=6

    # Question 1: Rate of cost increase (acceleration/deceleration)
    print("1. COST ACCELERATION ANALYSIS")
    daily_costs["daily_change"] = daily_costs["line_item_unblended_cost"].diff()
    daily_costs["acceleration"] = daily_costs["daily_change"].diff()

    avg_acceleration = daily_costs["acceleration"].mean()
    if avg_acceleration > 0:
        accel_desc = "accelerating (costs are increasing faster over time)"
    elif avg_acceleration < 0:
        accel_desc = "decelerating (rate of cost increase is slowing down)"
    else:
        accel_desc = "stable (consistent rate of change)"

    print(f"Average acceleration: ${avg_acceleration:.6f} per day")
    print(f"Interpretation: The rate of cost change is {accel_desc}")

    # Question 2: Cost variation by day of week
    print("\n2. COST VARIATION BY DAY OF WEEK")
    day_variation = (
        daily_costs.groupby("day_name")["line_item_unblended_cost"]
        .agg(["mean", "std", "count"])
        .round(2)
    )
    day_variation["cv"] = (day_variation["std"] / day_variation["mean"] * 100).round(
        2
    )  # Coefficient of variation

    print("Day of Week    | Mean Cost | Std Dev | CV (%) | Sample Size")
    print("----------------------------------------------------------")
    for day, row in day_variation.iterrows():
        print(
            f"{day:15} | ${row['mean']:8.2f} | ${row['std']:7.2f} | {row['cv']:5.2f}% | {row['count']:11}"
        )

    most_variable_day = day_variation["cv"].idxmax()
    print(
        f"\nMost variable day: {most_variable_day} (CV: {day_variation.loc[most_variable_day, 'cv']}%)"
    )

    # Question 3: Weekends vs Weekdays average costs
    print("\n3. WEEKEND VS WEEKDAY COST COMPARISON")
    weekend_weekday = (
        daily_costs.groupby("is_weekend")["line_item_unblended_cost"]
        .agg(["mean", "count"])
        .round(2)
    )

    weekday_avg = weekend_weekday.loc[False, "mean"]
    weekend_avg = weekend_weekday.loc[True, "mean"]
    ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 0

    print(f"Weekday average cost: ${weekday_avg:.2f}")
    print(f"Weekend average cost: ${weekend_avg:.2f}")
    print(f"Weekend/Weekday ratio: {ratio:.3f}")

    if ratio < 1:
        print("Conclusion: Weekends cost less than weekdays")
    else:
        print("Conclusion: Weekends cost more than weekdays")

    # Question 4: Day of week patterns
    print("\n4. DAILY COST PATTERNS BY DAY OF WEEK")
    day_patterns = (
        daily_costs.groupby("day_name")["line_item_unblended_cost"]
        .agg(["mean", "min", "max", "count"])
        .round(2)
        .sort_values("mean", ascending=False)
    )

    print("Day of Week    | Avg Cost | Min Cost | Max Cost | Days")
    print("------------------------------------------------------")
    for day, row in day_patterns.iterrows():
        print(
            f"{day:15} | ${row['mean']:8.2f} | ${row['min']:8.2f} | ${row['max']:8.2f} | {row['count']:4}"
        )

    return {
        # "acceleration": {
        #     "average_acceleration": avg_acceleration,
        #     "trend": accel_desc,
        #     "daily_changes": daily_costs["daily_change"].dropna().tolist(),
        # },
        # "day_variation": day_variation.to_dict(),
        # "weekend_weekday": {
        #     "weekday_avg": weekday_avg,
        #     "weekend_avg": weekend_avg,
        #     "ratio": ratio,
        #     "weekends_cheaper": ratio < 1,
        # },
        "day_patterns": day_patterns.to_dict(),
    }


def analyze_cost_spike(df):
    """Analyze cost spikes in the dataset"""
    print("\n=== COST SPIKE ANALYSIS ===")

    # Step 1: Aggregate cost by day
    daily_costs = (
        df.groupby("usage_date")["line_item_unblended_cost"]
        .sum()
        .reset_index()
        .sort_values("usage_date")
    )

    # Calculate rolling mean and standard deviation for spike detection
    daily_costs["rolling_mean"] = (
        daily_costs["line_item_unblended_cost"].rolling(window=7, center=True).mean()
    )
    daily_costs["rolling_std"] = (
        daily_costs["line_item_unblended_cost"].rolling(window=7, center=True).std()
    )

    # Calculate z-score for spike detection
    daily_costs["z_score"] = (
        daily_costs["line_item_unblended_cost"] - daily_costs["rolling_mean"]
    ) / daily_costs["rolling_std"]

    # Find spike days (z-score > 2)
    spike_days = daily_costs[daily_costs["z_score"] > 2].sort_values(
        "z_score", ascending=False
    )

    if len(spike_days) == 0:
        print("No significant cost spikes detected (z-score > 2)")
        return {"spike_detected": False}

    # Get the biggest spike
    main_spike = spike_days.iloc[0]
    spike_date = main_spike["usage_date"]
    spike_cost = main_spike["line_item_unblended_cost"]
    spike_z_score = main_spike["z_score"]

    print(f"Cost spike detected on {spike_date.strftime('%Y-%m-%d')}")

    # Step 2: Identify spike window (±1 day around spike)
    spike_window_start = spike_date - pd.Timedelta(days=1)
    spike_window_end = spike_date + pd.Timedelta(days=1)

    spike_window_data = df[
        (df["usage_date"] >= spike_window_start)
        & (df["usage_date"] <= spike_window_end)
    ]

    # Step 3: Break down by service (dimension)
    print("\nSpike period service breakdown:")
    service_spike_costs = (
        spike_window_data.groupby("line_item_product_code")["line_item_unblended_cost"]
        .sum()
        .reset_index()
        .sort_values("line_item_unblended_cost", ascending=False)
    )

    total_spike_cost = service_spike_costs["line_item_unblended_cost"].sum()
    service_spike_costs["percentage"] = (
        service_spike_costs["line_item_unblended_cost"] / total_spike_cost * 100
    ).round(2)

    print("Service                    | Cost ($)   | Percentage")
    print("---------------------------------------------------")

    # Step 4: Propose 2 possible reasons
    top_service = service_spike_costs.iloc[0]["line_item_product_code"]
    top_service_cost = service_spike_costs.iloc[0]["line_item_unblended_cost"]
    top_service_pct = service_spike_costs.iloc[0]["percentage"]

    print("\nPossible reasons for the cost spike:")
    print(
        f"1. {top_service} usage surge: {top_service} accounted for {top_service_pct}% of spike costs (${top_service_cost:.2f})"
    )
    print(
        "   - Possible causes: Auto-scaling events, increased workload, or configuration changes"
    )

    if len(service_spike_costs) > 1:
        second_service = service_spike_costs.iloc[1]["line_item_product_code"]
        print(
            f"2. {second_service} contribution: Additional costs from {second_service} and other services"
        )
        print(
            "   - Possible causes: Cross-service dependencies or cascading resource usage"
        )

    return {
        "spike_detected": True,
        "spike_date": spike_date.strftime("%Y-%m-%d"),
        "spike_cost": spike_cost,
        "z_score": spike_z_score,
        "top_service": top_service,
        "service_breakdown": service_spike_costs.set_index("line_item_product_code")[
            "line_item_unblended_cost"
        ].to_dict(),
    }


def main():
    """Main analysis function"""
    file_path = "cur_export.parquet"

    # Load data
    df = load_cur_data(file_path)

    # Run all analyses
    print(analyze_highest_cost_day(df))
    print(analyze_missing_resource_ids(df))
    # print(analyze_dataset_structure(df))
    print(analyze_top_spending_services(df))
    # print(analyze_cost_concentration(df))
    # print(analyze_cost_spike(df))
    # print(analyze_time_patterns(df))

    # Deep dive on EC2 (most common service)
    # print(analyze_service_deep_dive(df, "AmazonEC2"))


if __name__ == "__main__":
    main()
