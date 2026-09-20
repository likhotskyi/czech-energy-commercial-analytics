// ============================================================================
//  Power Query — the one transformation that is done in Power BI rather than
//  in Python, so it is visible in the query editor.
//
//  Home > Transform data > New Source > Blank Query
//  View > Advanced Editor > paste > replace the folder path on the first line
// ============================================================================

let
    // One place to change when the folder moves.
    Folder = "C:\Users\YOU\eu-energy-price-benchmark\powerbi\",

    Source = Csv.Document(
        File.Contents( Folder & "fact_components.csv" ),
        [ Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv ]
    ),

    Promoted = Table.PromoteHeaders( Source, [PromoteAllScalars = true] ),

    Typed = Table.TransformColumnTypes(
        Promoted,
        {
            { "geo",            type text },
            { "year",           Int64.Type },
            { "energy_supply",  type number },
            { "network_costs",  type number },
            { "taxes_excl_vat", type number },
            { "total_excl_vat", type number }
        }
    ),

    // The total has to go BEFORE unpivoting. Leave it in and it becomes a fourth
    // "component", every bar doubles in height and every share halves — and the
    // chart still looks perfectly reasonable, which is what makes it dangerous.
    WithoutTotal = Table.RemoveColumns( Typed, { "total_excl_vat" } ),

    // UnpivotOtherColumns rather than Unpivot: this way a new component column
    // added to the source later is picked up automatically instead of being
    // silently dropped.
    Unpivoted = Table.UnpivotOtherColumns(
        WithoutTotal,
        { "geo", "year" },
        "component_code",
        "value_eur_kwh"
    )
in
    Unpivoted

// ============================================================================
//  Result: one row per country x year x component, which is the shape a stacked
//  bar chart and the share measures both need.
//
//  63 rows in becomes 189 rows out (63 x 3 components).
//
//  The other five files load as they are — Get data > Text/CSV, no transforms.
//  Check that Power BI typed price_eur_kwh as a decimal number and not as text;
//  a decimal comma in a regional setting is the usual cause if it did not.
// ============================================================================
