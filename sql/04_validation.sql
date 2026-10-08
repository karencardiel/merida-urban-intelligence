DO $$
DECLARE geographic_count bigint;
BEGIN
    SELECT COUNT(*) INTO geographic_count FROM dim_ageb;
    IF geographic_count=0 THEN RAISE EXCEPTION 'Empty geographic dimension'; END IF;
    IF EXISTS (SELECT 1 FROM dim_ageb WHERE geometry IS NULL OR NOT ST_IsValid(geometry) OR ST_IsEmpty(geometry) OR ST_SRID(geometry)<>4326 OR area_km2<=0 OR area_km2 IS NULL) THEN
        RAISE EXCEPTION 'Invalid geographic dimension';
    END IF;
    IF (SELECT COUNT(*) FROM fact_demografia)<>geographic_count OR
       (SELECT COUNT(*) FROM fact_economia)<>geographic_count OR
       (SELECT COUNT(*) FROM fact_accidentes)<>geographic_count THEN
        RAISE EXCEPTION 'Main fact row counts differ from geography';
    END IF;
    IF (SELECT SUM(total_accidentes) FROM fact_accidentes) IS DISTINCT FROM
       (SELECT SUM(total_accidentes) FROM fact_accidentes_tiempo) THEN
        RAISE EXCEPTION 'Temporal accidents do not reconcile';
    END IF;
    IF EXISTS (SELECT 1 FROM fact_economia WHERE total_establecimientos IS NULL OR total_establecimientos<0 OR retail IS NULL OR comercio+servicios+otros<>total_establecimientos OR retail>comercio) THEN
        RAISE EXCEPTION 'Economic counts do not reconcile';
    END IF;
    IF EXISTS (SELECT 1 FROM fact_accidentes WHERE total_accidentes IS NULL OR total_accidentes<0 OR total_accidentes <> accidentes_tipo_1+accidentes_tipo_2+accidentes_tipo_4+accidentes_tipo_5+accidentes_tipo_6+accidentes_tipo_7+accidentes_tipo_8+accidentes_tipo_10+accidentes_tipo_11) THEN
        RAISE EXCEPTION 'Accident types do not reconcile';
    END IF;
    IF EXISTS (SELECT 1 FROM fact_demografia WHERE "POBTOT"<0 OR tasa_pea<0 OR tasa_pea>100) THEN
        RAISE EXCEPTION 'Invalid demographic metrics';
    END IF;
END $$;
SELECT 'dim_ageb' AS table_name,COUNT(*) FROM dim_ageb
UNION ALL SELECT 'fact_demografia',COUNT(*) FROM fact_demografia
UNION ALL SELECT 'fact_economia',COUNT(*) FROM fact_economia
UNION ALL SELECT 'fact_accidentes',COUNT(*) FROM fact_accidentes
UNION ALL SELECT 'fact_accidentes_tiempo',COUNT(*) FROM fact_accidentes_tiempo;
