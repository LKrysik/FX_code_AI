# ===================================================================================
# NOWY SPOSÓB (od wersji 3.15) - operation_type: "Incremental Table"
# ===================================================================================

**Teraz create_incremental_table jest zintegrowany jako operation_type w metadata_json!**
Zamiast osobnej funkcji, wystarczy użyć standardowego create_table() z odpowiednim operation_type.

## Przykład użycia - Nowy sposób (uproszczony):

```python
metadata_json = '''
{
    "target_table": {
        "target_schema": "output",
        "target_table": "lorax_dim_component_hybrid",
        "format": "delta",
        "operation_type": "Incremental Table",
        "incremental_params": {
            "id_key_column": "src_agnostic_unique_id",
            "included_columns_for_hash": null,
            "excluded_columns_for_hash": null,
            "log_history": true,
            "history_table_name": "lorax_dim_component_hybrid_delta_log",
            "history_retention_days": 30,
            "ignore_new_columns_as_change": true
        },
        "params": {"skip_data_lineage": true}
    },
    "source_tables": [
        {"schema": "process", "table": "lorax_dim_component_hybrid", "view": "source"}
    ],
    "env": "'''+ str(ENV) +'''",
    "project_name": "'''+ str(PROJECT_NAME) +'''"
}
'''

# Instantiate temp views and define target table (with env)
make_env_tables(metadata_json)

# Przygotuj dane źródłowe (opcjonalnie - możesz też użyć danych bezpośrednio z view)
df = spark.sql("SELECT * FROM source")

# Wykonaj operację inkrementalną - wszystko automatycznie!
df_result = create_table(metadata_json, df)

print(f"✓ Incremental operation completed!")
```

**Zalety nowego sposobu:**
- ✅ **3 linie kodu** zamiast 50+
- ✅ Spójna składnia z innymi operation_type
- ✅ Automatyczne wykrycie Full Load vs Delta Load
- ✅ Wszystkie parametry w jednym miejscu (metadata_json)
- ✅ Obsługa zarówno `operation_type` jak i `opertation_type` (backward compatibility)
- ✅ Automatyczne wykrywanie Insert/Update/Delete
- ✅ Historia zmian (opcjonalna)
- ✅ Schema evolution (nowe kolumny)

## Parametry incremental_params:

| Parametr | Typ | Opis |
|----------|-----|------|
| `id_key_column` | string (required) | Klucz główny do porównywania rekordów |
| `included_columns_for_hash` | list lub null | Kolumny śledzone dla zmian (null = wszystkie) |
| `excluded_columns_for_hash` | list lub null | Kolumny ignorowane w detekcji zmian |
| `log_history` | boolean | Czy zapisywać historię zmian do tabeli audytowej |
| `history_table_name` | string | Nazwa tabeli z historią zmian |
| `history_retention_days` | int | Ile dni przechowywać historię (automatyczne czyszczenie) |
| `ignore_new_columns_as_change` | boolean | Czy nowe kolumny w source nie powodują Update |

## Jak to działa:

1. **Full Load** (jeśli target nie istnieje):
   - Tworzy tabelę z danymi z `source_tables`
   - Dodaje kolumny: `operation_type='I'`, `last_update_dt=current_timestamp()`

2. **Delta Load** (jeśli target istnieje):
   - Używa zarówno `source_tables` (dane źródłowe) jak i tabeli target
   - Wykrywa zmiany: Insert, Update (tracked/untracked), Delete, Reactivate
   - Zapisuje zmiany do tabeli target
   - Opcjonalnie loguje do tabeli historii

---

# ===================================================================================
# STARY SPOSÓB (przed wersją 3.15) - create_incremental_table() - LEGACY
# ===================================================================================

**UWAGA: Poniższy sposób jest przestarzały. Użyj nowego sposobu z `operation_type: "Incremental Table"`**

Obecnie jak działa create_incremental_table (LEGACY - nie zalecane)

metadata_full_load = '''
    {
        "target_table": {"target_schema":"output", "target_table":"lorax_dim_component_hybrid", "format":"delta", "opertation_type":"Managed Table Type"},
        "source_tables": [
            {"schema":"process",    "table":"lorax_dim_component_hybrid",       "view":"source"}
        ],
        "env": "'''+str(ENV)+'''",
        "project_name": "'''+str(PROJECT_NAME)+'''",
        "admin_schema_name": "'''+str(admin_schema_name)+'''",
        "admin_table_name_to_output": "'''+str(admin_table_name_to_output)+'''",
        "process_date": "'''+str(process_date)+'''"
    }
'''

metadata_delta_load = '''
    {
        "target_table": {"target_schema":"output", "target_table":"lorax_dim_component_hybrid", "format":"delta","opertation_type":"Managed Table Type - Merge by Key","merge_condition":"target.src_agnostic_unique_id = source.src_agnostic_unique_id"},
        "source_tables": [
            {"schema":"process",    "table":"lorax_dim_component_hybrid",       "view":"source"},
            {"schema":"output",     "table":"lorax_dim_component_hybrid",       "view":"target"}
        ],
        "env": "'''+str(ENV)+'''",
        "project_name": "'''+str(PROJECT_NAME)+'''",
        "admin_schema_name": "'''+str(admin_schema_name)+'''",
        "admin_table_name_to_output": "'''+str(admin_table_name_to_output)+'''",
        "process_date": "'''+str(process_date)+'''"
    }
'''

target_table_name = get_table_env_name("output", "lorax_dim_component_hybrid", ENV, PROJECT_NAME, False, False)
source_table_name =  get_table_env_name("process", "lorax_dim_component_hybrid", ENV, PROJECT_NAME, False, False)
history_table_name = get_table_env_name("process", "lorax_dim_component_hybrid_delta_log", ENV, PROJECT_NAME, False, False)

print(f"Create delta table: {history_table_name} from {target_table_name} and {source_table_name}")

df = create_incremental_table(
    id_key_column="src_agnostic_unique_id",
    target_table_name=target_table_name,
    source_table_name=source_table_name,
    metadata_full_load=metadata_full_load,
    metadata_delta_load=metadata_delta_load,
    create_table_params={"skip_data_lineage": True},
    included_columns_for_hash=None,
    excluded_columns_for_hash=None,
    log_history=True,
    history_table_name=history_table_name,
    history_retention_days=30
)



A ja chce żeby to było podobnie do kodu z użyciem metadata_json


## ------------------------------------------------------------------------------------
metadata_json = '''
{
    "target_table": {"target_schema": "output", "target_table": "lorax_dim_plant", "format":"delta","opertation_type":"Managed Table Type", "params":{"drop_table":"True"}},
    "source_tables": [
        {"schema":"output",     "table":"dim_plant",                    "view":"dim_plant",                           "project_name":"ods"},
        {"schema":"process",    "table":"lorax_dim_bill_of_material",   "view":"lorax_dim_bill_of_material"},
        {"schema":"process",    "table":"lorax_fact_purchase_actuals",  "view":"lorax_fact_purchase_actuals"},
        {"schema":"process",    "table":"lorax_fact_shipment_actuals",  "view":"lorax_fact_shipment_actuals"}
    ],
    "env": "'''+str(ENV)+'''",
    "project_name": "'''+str(PROJECT_NAME)+'''",
    "admin_schema_name": "'''+str(admin_schema_name)+'''",
    "admin_table_name_to_output": "'''+str(admin_table_name_to_output)+'''",
    "process_date": "'''+str(process_date)+'''"
}
'''
#Instantiate temp vies and define target table (with env)
make_env_tables(metadata_json)

## ------------------------------------------------------------------------------------

df = spark.sql("""
    WITH plant_list AS (
        SELECT      header_plant                        AS plant_cd     FROM    lorax_dim_bill_of_material
        UNION ALL
        SELECT      plant                               AS plant_cd     FROM    lorax_dim_bill_of_material
        UNION ALL
        SELECT      receiving_plant                     AS plant_cd     FROM    lorax_fact_purchase_actuals
        UNION ALL
        SELECT      sending_plant                       AS plant_cd     FROM    lorax_fact_purchase_actuals
        UNION ALL
        SELECT      manuf_plant_code                    AS plant_cd     FROM    lorax_fact_purchase_actuals
        UNION ALL
        SELECT      plant                               AS plant_cd     FROM    lorax_fact_shipment_actuals
        UNION ALL
        SELECT      manuf_plant_code                    AS plant_cd     FROM    lorax_fact_shipment_actuals
    )

    SELECT      a.*
    FROM        dim_plant a
    SEMI JOIN   plant_list b
        ON      a.src_agnostic_unique_id = b.plant_cd
""").drop("_run_id", "_run_timestamp")

## ------------------------------------------------------------------------------------
create_table(metadata_json, df)


inny przykłąd kodu

## ------------------------------------------------------------------------------------
metadata_json = '''
{
    "target_table": {"target_schema": "process", "target_table": "lorax_bom_exclusion_rule_2_validation", "format":"delta","opertation_type":"Managed Table Type", "partitionBy":["exclusion_rule"], "params":{"drop_table":"True"}},
    "source_tables": [
                {"schema":"output",         "table":"dim_material",                 "view":"dim_material",                  "project_name":"ods"},
                {"schema":"process",        "table":"lorax_dim_component_hybrid",   "view":"lorax_dim_component_hybrid"},
                {"schema":"process",        "table":"lorax_dim_bill_of_material",   "view":"lorax_dim_bill_of_material"},
                {                           "table":"dbo.GlobalOptionsetMetadata",  "view":"df_choice",  "linked_service_name":"DATAVERSE_SL_SQL_LS", "opertation_type":"serverless jdbc ls"}
    ],
    "env": "'''+str(ENV)+'''",
    "project_name": "'''+str(PROJECT_NAME)+'''"
}
'''
#Instantiate temp vies and define target table (with env)
make_env_tables(metadata_json)

## ------------------------------------------------------------------------------------
# This table can be used to check results of the rule 2 detemination
## ------------------------------------------------------------------------------------

df = spark.sql("""
    SELECT      DISTINCT
                bom.level,
                bom.header_material,
                mat_hdr.description                                         AS header_material_description,
                mat_hdr.Traded_Unit_Format,
                mat_hdr.Brand_Flag,
                mat_hdr.Consumer_Pack_Format,
                mat_hdr.EC_Group,
                bom.level_material,
                mat_lvl.description                                         AS level_material_description,
                bom.bom_component,
                comp.component_description,
                comp.component_weight_g,
                comp.component_usage,
                comp.component_category,
                comp.component_subcategory,
                comp.component_pack_group,
                bom.exclusion_rule,
                bom.exclusion_flag,
                bom.key,
                ch.LocalizedLabel                                           AS key_description
    FROM        lorax_dim_bill_of_material bom
    JOIN        dim_material mat_hdr
        ON      bom.header_material = mat_hdr.src_agnostic_unique_id
    JOIN        lorax_dim_component_hybrid comp
        ON      bom.bom_component = comp.src_agnostic_unique_id
    JOIN        dim_material mat_lvl
        ON      bom.level_material = mat_lvl.src_agnostic_unique_id
    LEFT JOIN   df_choice ch
        ON      ch.Option = bom.key
        AND     ch.GlobalOptionSetName = 'cr579_copackwasteaccesssequence'
    WHERE       bom.level > 1
        AND     UPPER(comp.component_usage) NOT LIKE '%TERTIARY%'
    ORDER BY    mat_hdr.Traded_Unit_Format,
                mat_hdr.Brand_Flag,
                bom.header_material
""")

## ------------------------------------------------------------------------------------
create_table(metadata_json, df)


inny przykład kodu metadata_json


## ------------------------------------------------------------------------------------
metadata_json = '''
{
    "target_table": {"target_schema": "process", "target_table": "lorax_dim_component_hybrid", "format":"delta","opertation_type":"Managed Table Type", "params":{"drop_table":"True"}},
    "source_tables": [
        {"schema":"output",     "table":"dim_component_hybrid",                         "view":"dim_component_hybrid",                          "project_name":"ods"},
        {"schema":"output",     "table":"lorax_dim_bill_of_material_persist_history",   "view":"lorax_dim_bill_of_material_persist_history",    "params":{"optional":"True"}},
        {"schema":"process",    "table":"lorax_fact_purchase_actuals",                  "view":"lorax_fact_purchase_actuals"},
        {"schema":"process",    "table":"lorax_dim_bill_of_material",                   "view":"lorax_dim_bill_of_material"}
    ],
    "env": "'''+str(ENV)+'''",
    "project_name": "'''+str(PROJECT_NAME)+'''"
}
'''
#Instantiate temp vies and define target table (with env)
make_env_tables(metadata_json)

## ------------------------------------------------------------------------------------

df = spark.sql("""
    -- Get list of Components ; need to pick up from Purchasing Actuals, and from various BOM tables
    SELECT  material_number
    FROM    lorax_fact_purchase_actuals
    WHERE   flow LIKE 'R&P%'
    UNION ALL
    SELECT  bom_component                           AS material_number
    FROM    lorax_dim_bill_of_material
""").createOrReplaceTempView("component_list")

# If LORAX BOM Version table exists, check for additional components there too and add them
# Since BOM Version comes *later* in the process, this check is optional / conditioned on the table's existence (to avoid a chicken/egg situation)
chk_tbl_1 = delta_table_exists("lorax_dim_bill_of_material_persist_history")

if chk_tbl_1:
    spark.sql("""
        SELECT  *
        FROM    component_list
        UNION
        SELECT  bom_component                       AS material_number
        FROM    lorax_dim_bill_of_material_persist_history
    """).createOrReplaceTempView("component_list")
else:
    print("Skipping BOM Version table - table not found ...")

# Final output ...
df = spark.sql("""
    SELECT      a.*
    FROM        dim_component_hybrid a
    SEMI JOIN   component_list b
        ON      a.src_agnostic_unique_id = b.material_number
    WHERE       a.material_type IN ('VERP', 'ZQFC')             -- this filter shouldn't be needed as the same filter is already used on BOM ; yet we somehow ended up 
                                                                --   with some UNBWs in there anyway, so need to keep the filter here as well :-(
""").drop("_run_id", "_run_timestamp")

## ------------------------------------------------------------------------------------
create_table(metadata_json, df)




inny przykład kodu metadata_json

metadata_json = '''
{
    "target_table": {"target_schema": "process", "target_table": "lorax_fact_shipment_actuals", "format": "delta","opertation_type": "Managed Table Type", "params":{"drop_table":"True"}},
    "source_tables": [
        {"schema":"output",             "table":"fact_shipment_actuals",    "view":"fact_shipment_actuals",     "project_name":"ods"},
        {"schema":"output",             "table":"dim_customer",             "view":"dim_customer",              "project_name":"ods"},
        {"schema":"output",             "table":"dim_material",             "view":"dim_material",              "project_name":"ods"},
        {                               "table":"dbo.v_odsrules",           "view":"v_odsrules",                "linked_service_name":"DATAVERSE_SL_SQL_LS", "opertation_type":"serverless jdbc ls"}
    ],
    "env": "'''+str(ENV)+'''",
    "project_name": "'''+str(PROJECT_NAME)+'''",
    "admin_schema_name": "'''+str(admin_schema_name)+'''",
    "admin_table_name_to_process": "'''+str(admin_table_name_to_process)+'''",
    "process_date": "'''+str(process_date)+'''"
}
'''
#Instantiate temp vies and define target table (with env)
make_env_tables(metadata_json)

## ------------------------------------------------------------------------------------

df = spark.sql("""
    WITH sales_organizations_to_include AS (
        SELECT  value1                                          AS condition_1
        FROM    v_odsrules
        WHERE   function = 'SALES_ACTUALS_ODS'
        AND     criteria = 'SALES_ORG_OUT_LORAX'
    ), 
    ods_rules_ship_to_country_exclusion AS (
        SELECT  value1                                          AS condition_1,
                value2                                          AS condition_2,
                result1                                         AS result_rule
        FROM    v_odsrules
        WHERE   function = 'SALES_ACTUALS_ODS'
        AND     criteria = 'SHIP_TO_COUNTRY_EXCLUSION'
    ),
    ods_rules_market_segment AS (
        SELECT  value1                                          AS market_segment
        FROM    v_odsrules
        WHERE   function = 'SALES_ACTUALS_ODS'
            AND criteria = 'MARKET_SEGMENT_EXCLUSION'
    )

    -- Apply market segment & sales org filters ; apply ship-to country exclusion (update 'flow' accordingly)
    SELECT      fsa.*,
                CONCAT(fsa.flow, IFNULL(NULLIF(CONCAT(' - ', orstce.result_rule), ' - '), ''))  AS flow_final
    FROM        fact_shipment_actuals fsa
    SEMI JOIN   sales_organizations_to_include soti 
        ON      soti.condition_1    = fsa.sales_organization
    JOIN        dim_material mat
        ON      fsa.material_number = mat.src_agnostic_unique_id
        AND     mat.material_type   = 'FERT'
    LEFT JOIN   dim_customer ldc 
        ON      fsa.ship_to_party   = ldc.src_agnostic_unique_id
    LEFT JOIN   ods_rules_ship_to_country_exclusion orstce 
        ON      orstce.condition_1  = fsa.sales_organization 
        AND     orstce.condition_2  = ldc.country_key 
    ANTI JOIN   ods_rules_market_segment o
        ON      mat.market_segment  = o.market_segment 
""").withColumn("flow", F.col("flow_final")).drop("flow_final")

## ------------------------------------------------------------------------------------
create_table(metadata_json, df)