from __future__ import annotations

from business_data_pipelines.pipelines.qnh.activity_detail.models import DimensionConfig


ACTIVITY_DIMENSION = DimensionConfig(
    name="activity",
    data_source_name="活动明细-活动-活动维度",
    view_code="qnh_promotion_analysis_promotion_promotion",
    target_table="activity_detail",
    expected_task_prefix="导出活动明细",
    et_env_name="QNH_ACTIVITY_ET",
    selected_data_codes=[
        "act_ord_cnt",
        "act_ord_pen_rate",
        "act_ord_sale_amt_gmv",
        "act_ord_sale_income",
        "act_txn_poi_cnt",
        "act_poi_promo_amt",
        "act_plat_promo_amt",
        "act_prod_num",
        "act_prod_cnt",
    ],
    has_store_column=False,
    has_active_store_count=True,
)

STORE_DIMENSION = DimensionConfig(
    name="store",
    data_source_name="活动明细-活动-门店维度",
    view_code="qnh_promotion_analysis_promotion_store",
    target_table="activity_detail_store",
    expected_task_prefix="导出门店活动明细",
    et_env_name="QNH_STORE_ET",
    selected_data_codes=[
        "act_ord_cnt",
        "act_ord_pen_rate",
        "act_ord_sale_amt_gmv",
        "act_ord_sale_income",
        "act_poi_promo_amt",
        "act_plat_promo_amt",
        "act_prod_num",
        "act_prod_cnt",
    ],
    has_store_column=True,
    has_active_store_count=False,
)


DIMENSIONS = {
    ACTIVITY_DIMENSION.name: ACTIVITY_DIMENSION,
    STORE_DIMENSION.name: STORE_DIMENSION,
}

