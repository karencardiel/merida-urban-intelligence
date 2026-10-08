"""KPI maps and spatial statistics, using PostgreSQL as the only analytical source."""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy.stats import pearsonr,spearmanr
from sqlalchemy import create_engine
from libpysal.weights import Queen,lag_spatial
from esda.moran import Moran,Moran_Local,Moran_BV
from .config import OUTPUTS,database_url

SEED=42
PERMUTATIONS=999

LABELS = {
    'densidad_pob_km2': 'Population density (residents/km²)',
    'densidad_establecimientos_km2': 'Business density (establishments/km²)',
    'densidad_accidentes_km2': 'Traffic accident density (accidents/km²)',
}
CLUSTER_COLORS = {
    'High-High': '#d73027',
    'Low-Low': '#4575b4',
    'High-Low': '#fdae61',
    'Low-High': '#abd9e9',
    'Not significant': '#e0e0e0',
    'No neighbors': '#595959',
}

def draw_map(gdf, column, title, path, categorical=False):
    fig, ax = plt.subplots(figsize=(9, 9))
    if categorical:
        colors = gdf[column].map(CLUSTER_COLORS)
        if colors.isna().any():
            raise ValueError('Unknown LISA cluster label.')
        gdf.plot(color=colors, ax=ax, edgecolor='white', linewidth=.15)
        handles = [Patch(facecolor=color, label=label)
                   for label, color in CLUSTER_COLORS.items()]
        ax.legend(handles=handles, title='Local association', loc='upper right')
    else:
        gdf.plot(column=column, ax=ax, legend=True, cmap='viridis',
                 edgecolor='white', linewidth=.1,
                 legend_kwds={'label': LABELS.get(column, column), 'shrink': .75},
                 missing_kwds={'color': 'lightgray', 'label': 'Missing'})
    ax.set_title(title)
    ax.set_axis_off()
    note = 'Mérida urban locality · AGEB boundaries'
    if categorical:
        note += '\n999 permutations · unadjusted p < 0.05 · exploratory clusters'
    fig.text(.5, .015, note, ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .045, 1, 1))
    fig.savefig(path, dpi=180, bbox_inches='tight')
    plt.close(fig)

def draw_correlation(sample, x, y, path, coefficients):
    """Show the raw scale and a log1p view without removing any observation."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax in axes:
        ax.scatter(sample[x], sample[y], s=14, alpha=.6, edgecolors='none')
        ax.set_xlabel(LABELS[x])
        ax.set_ylabel(LABELS[y])
        ax.grid(alpha=.15)
    axes[0].set_title('Original scale · all AGEBs')
    axes[1].set_title('Log1p axes · all AGEBs (zeros retained)')
    axes[1].set_xlim(0, float(sample[x].max()) * 1.05)
    axes[1].set_ylim(0, float(sample[y].max()) * 1.05)
    # Tick labels remain in original units. Only the display changes.
    for axis in ['x', 'y']:
        getattr(axes[1], 'set_' + axis + 'scale')(
            'function', functions=(np.log1p, np.expm1))
        maximum = float(sample[x if axis == 'x' else y].max()) * 1.05
        ticks = [0] + [10.0 ** power for power in range(0, 8)
                       if 10.0 ** power <= maximum]
        getattr(axes[1], 'set_' + axis + 'ticks')(ticks)
    for ax in axes:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:,.0f}'))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:,.0f}'))
    fig.suptitle('Association across urban AGEBs')
    fig.text(.5, .02,
             f"n = {len(sample)} · Pearson r = {coefficients['Pearson']:.3f} · "
             f"Spearman ρ = {coefficients['Spearman']:.3f} · "
             'Coefficients computed on the original data',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .94))
    fig.savefig(path, dpi=180, bbox_inches='tight')
    plt.close(fig)

def run_analysis():
    engine=create_engine(database_url())
    try:
        gdf=gpd.read_postgis('SELECT * FROM vw_analisis_ageb ORDER BY "CVE_AGEB"',engine,geom_col='geometry').reset_index(drop=True)
        temporal=pd.read_sql('SELECT * FROM fact_accidentes_tiempo ORDER BY "CVE_AGEB",anio,mes,periodo_dia',engine)
    finally:
        engine.dispose()
    if gdf.empty or gdf.CVE_AGEB.duplicated().any():
        raise ValueError('Warehouse geographic dataset is empty or duplicated.')
    for d in ['maps','figures','tables']:(OUTPUTS/d).mkdir(parents=True,exist_ok=True)
    gdf.drop(columns='geometry').to_csv(OUTPUTS/'tables/kpis_ageb.csv',index=False)
    temporal.to_csv(OUTPUTS/'tables/accidentes_tiempo.csv',index=False)
    indicators=['densidad_pob_km2','densidad_establecimientos_km2','densidad_accidentes_km2']
    titles=['Population density per km²','Business density per km²','Traffic accident density per km²']
    for column,title in zip(indicators,titles):draw_map(gdf,column,title,OUTPUTS/f'maps/{column}.png')
    pairs=[(indicators[0],indicators[1]),(indicators[0],indicators[2]),(indicators[1],indicators[2])]
    correlations=[]
    for x,y in pairs:
        sample=gdf[[x,y]].replace([np.inf,-np.inf],np.nan).dropna()
        if len(sample)<3 or sample[x].nunique()<2 or sample[y].nunique()<2:raise ValueError(f'Insufficient data for correlation {x}, {y}.')
        coefficients = {}
        for method,function in [('Pearson',pearsonr),('Spearman',spearmanr)]:
            coef,pvalue=function(sample[x],sample[y]);coefficients[method]=float(coef);correlations.append({'x':x,'y':y,'method':method,'n':len(sample),'coefficient':float(coef),'p_value':float(pvalue)})
        draw_correlation(sample, x, y, OUTPUTS/f'figures/correlation_{x}_{y}.png', coefficients)
    # Preserve the AGEB context of extreme densities for review, without deleting rows.
    extreme_rows = []
    for field in indicators:
        for _, row in gdf.nlargest(5, field).iterrows():
            extreme_rows.append({'indicator': field, 'CVE_AGEB': row.CVE_AGEB,
                                 'density': row[field], 'area_km2': row.area_km2,
                                 'population': row.POBTOT,
                                 'businesses': row.total_establecimientos,
                                 'accidents': row.total_accidentes})
    pd.DataFrame(extreme_rows).to_csv(OUTPUTS/'tables/extreme_density_agebs.csv', index=False)
    pd.DataFrame(correlations).to_csv(OUTPUTS/'tables/correlations.csv',index=False)
    # Every variable shares the same ordered geographic dataset and weights.
    for field in indicators:
        if not np.isfinite(gdf[field].to_numpy(dtype=float)).all():raise ValueError(f'Nonfinite spatial indicator {field}.')
    w=Queen.from_dataframe(gdf,ids=gdf.CVE_AGEB.tolist())
    w.transform='r'
    neighbors=np.array([len(w.neighbors[key]) for key in gdf.CVE_AGEB])
    island=neighbors==0
    global_results=[]
    for field in [indicators[0],indicators[2]]:
        np.random.seed(SEED)
        model=Moran(gdf[field].to_numpy(),w,permutations=PERMUTATIONS)
        global_results.append({'indicator':field,'I':float(model.I),'expected_I':float(model.EI),'p_sim':float(model.p_sim),'permutations':PERMUTATIONS})
        local=Moran_Local(gdf[field].to_numpy(),w,permutations=PERMUTATIONS,seed=SEED,n_jobs=1)
        labels=np.full(len(gdf),'Not significant',dtype=object)
        significant=(local.p_sim<.05)&~island
        for quadrant,label in [(1,'High-High'),(2,'Low-High'),(3,'Low-Low'),(4,'High-Low')]:labels[(local.q==quadrant)&significant]=label
        labels[island]='No neighbors'
        frame=gdf[['CVE_AGEB','geometry']].copy();frame['cluster']=labels
        frame['local_I']=local.Is;frame['p_sim']=np.where(island,np.nan,local.p_sim)
        frame.drop(columns='geometry').to_csv(OUTPUTS/f'tables/lisa_{field}.csv',index=False)
        draw_map(frame,'cluster',f'LISA: {LABELS[field]}',OUTPUTS/f'maps/lisa_{field}.png',categorical=True)
    np.random.seed(SEED)
    bivariate=Moran_BV(gdf[indicators[1]].to_numpy(),gdf[indicators[2]].to_numpy(),w,permutations=PERMUTATIONS)
    summary={'scope':'Road safety using instructor-authorized ATUS; these are not crime indicators.','neighborhood':'Queen contiguity, row standardized; all AGEBs retained; islands have zero spatial lag and are excluded from local cluster classification.','islands':list(map(str,w.islands)),'components':int(w.n_components),'seed':SEED,'global_moran':global_results,'bivariate_moran':{'x':indicators[1],'neighbor_y':indicators[2],'I':float(bivariate.I),'p_sim':float(bivariate.p_sim),'permutations':PERMUTATIONS},'totals':{'ageb_count':len(gdf),'population':float(gdf.POBTOT.sum()),'businesses':float(gdf.total_establecimientos.sum()),'accidents':float(gdf.total_accidentes.sum())},'cautions':['Spatial association does not establish causality.','2020 population, 2024 accidents and the DENUE snapshot are not a single contemporaneous year.','LISA p-values are unadjusted exploratory results across multiple local tests.','Global Moran includes disconnected components and islands; assess sensitivity if required.','Densities share an area denominator and can show associations partly related to that denominator.','Traffic accidents per resident are a territorial indicator, not an individual travel-risk estimate.']}
    (OUTPUTS/'tables/spatial_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    fig,ax=plt.subplots(figsize=(7,5));x=gdf[indicators[1]].to_numpy();y=gdf[indicators[2]].to_numpy();zx=(x-x.mean())/x.std();zy=(y-y.mean())/y.std();ax.scatter(zx,lag_spatial(w,zy),s=10,alpha=.6);ax.axhline(0,color='gray',linewidth=.7);ax.axvline(0,color='gray',linewidth=.7);ax.set_xlabel('Standardized business density');ax.set_ylabel('Spatial lag of standardized accident density');ax.set_title(f'Bivariate Moran I = {bivariate.I:.3f}');fig.tight_layout();fig.savefig(OUTPUTS/'figures/bivariate_moran.png',dpi=180);plt.close(fig)
    monthly=temporal.groupby(['anio','mes']).total_accidentes.sum().reset_index()
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(monthly.mes,monthly.total_accidentes);ax.set_xlabel('Month');ax.set_ylabel('Traffic accidents');ax.set_xticks(range(1,13));fig.tight_layout();fig.savefig(OUTPUTS/'figures/accidents_by_month.png',dpi=180);plt.close(fig)
    lines=['# Findings from the warehouse','','## Geographic scope','','Urban AGEBs of the locality of Mérida. ATUS was authorized by the instructor as the road-safety source.','','## Totals','',f"{len(gdf)} AGEBs; {gdf.POBTOT.sum():,.0f} residents; {gdf.total_establecimientos.sum():,.0f} businesses; {gdf.total_accidentes.sum():,.0f} accidents.",'','## Correlations','']
    for item in correlations:
        lines.append(f"- {item['method']} {item['x']} vs {item['y']}: coefficient {item['coefficient']:.4f}, p {item['p_value']:.4g}, n {item['n']}.")
    lines+=['','## Spatial associations','']
    for item in global_results:
        interpretation='evidence of spatial clustering' if item['I']>0 and item['p_sim']<.05 else 'no significant positive spatial clustering at the chosen threshold'
        lines.append(f"- {item['indicator']}: Moran I {item['I']:.4f}, permutation p {item['p_sim']:.4g}; {interpretation}.")
    lines.append(f'- Business density and neighboring accident density: bivariate Moran I {bivariate.I:.4f}, permutation p {bivariate.p_sim:.4g}. This statistic relates businesses in an area to accidents in neighboring areas.')
    lines+=['','## Interpretation cautions','']+['- '+s for s in summary['cautions']]
    (OUTPUTS/'findings.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False));return summary
