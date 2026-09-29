"""CM-TV ECR Digital Twin — Step 09.V2.1 Portfolio Edition.
Run: python -m streamlit run 09_V2_1_ECR_LinkedIn_Portfolio.py --server.port 8504
CSV data remain separate: Step 08 macro calibration, Step 05-07 synthetic case.
"""
from pathlib import Path
from io import BytesIO
from datetime import datetime
import html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

ROOT=Path(__file__).resolve().parent
P={
 'road':ROOT/'output_step02_road_network'/'03_ECR_Road_Routes_Detail.csv',
 'cost':ROOT/'output_step03_road_transport_cost'/'02_ECR_Road_Transport_Cost_Detail.csv',
 'ops':ROOT/'output_step05_operational_dataset_V2'/'01_ECR_Operational_Dataset_90Days_V2.csv',
 'ops_summary':ROOT/'output_step05_operational_dataset_V2'/'02_ECR_Depot_Type_Summary_V2.csv',
 'movements':ROOT/'output_step06_MILP'/'01_ECR_Optimized_Movements.csv',
 'inventory':ROOT/'output_step06_MILP'/'02_ECR_Optimized_Inventory.csv',
 'kpi':ROOT/'output_step06_MILP'/'03_ECR_Optimization_KPI.csv',
 'routes':ROOT/'output_step06_MILP'/'04_ECR_Route_Summary.csv',
 'daily_kpi':ROOT/'output_step06_MILP'/'05_ECR_Daily_KPI.csv',
 'sensitivity':ROOT/'output_step07_sensitivity_analysis'/'01_ECR_Sensitivity_Summary.csv',
 'public':ROOT/'output_step08_reality_calibration_V2'/'01_ECR_V2_Public_Reference_Data.csv',
 'assumptions':ROOT/'output_step08_reality_calibration_V2'/'02_ECR_V2_Calibration_Assumptions.csv',
 'macro_summary':ROOT/'output_step08_reality_calibration_V2'/'04_ECR_V2_Network_Summary.csv',
 'macro_depots':ROOT/'output_step08_reality_calibration_V2'/'05_ECR_V2_Depot_Type_Summary.csv',
}
for scenario in ('LOW','BASE','HIGH'):
 P['macro_'+scenario]=ROOT/'output_step08_reality_calibration_V2'/f'03_ECR_Reality_Calibrated_V2_{scenario}.csv'

TERMINALS=[('T01_CMIT','CMIT','Cai Mep International Terminal',10.513779,107.019311,1100000),('T02_TCIT','TCIT','Tan Cang Cai Mep International Terminal',10.534163,107.034460,2248119),('T03_SSIT','SSIT','SP-SSA International Terminal',10.504844,107.010502,1000000)]
DEPOTS=[('D01_PHU_MY','D01','MEDLOG Phu My ICD',10.533846,107.054027,.35),('D02_CAI_MEP','D02','Logistics Cai Mep / ICD Cai Mep',10.555195,107.046862,.35),('D03_LONG_SON','D03','LSIP / Long Son International Port',10.471805,107.054136,.30)]
COORD={r[0]:(r[3],r[4]) for r in TERMINALS+DEPOTS}
ALIASES={'D01':'D01_PHU_MY','D02':'D02_CAI_MEP','D03':'D03_LONG_SON','D01_PHU_MY':'D01_PHU_MY','D02_CAI_MEP':'D02_CAI_MEP','D03_LONG_SON':'D03_LONG_SON'}

def col(df,*options):
 if df.empty:return None
 lookup={str(c).strip().lower().replace(' ','_'):c for c in df.columns}
 for option in options:
  key=option.strip().lower().replace(' ','_')
  if key in lookup:return lookup[key]
 return None

def number(x,default=0):
 try:return float(str(x).replace(',',''))
 except (ValueError,TypeError):return default

def metric(df,*names):
 if df.empty:return None
 if col(df,*names):return number(df.iloc[0][col(df,*names)],None)
 key=col(df,'KPI','Metric','Parameter','Name');value=col(df,'Value','Result','KPI_Value')
 if key and value:
  for n in names:
   z=df[df[key].astype(str).str.lower().str.strip()==n.lower()]
   if len(z):return number(z.iloc[0][value],None)
 return None

def integer(v):return f'{v:,.0f}' if v is not None else 'N/A'
def money(v):return f'{v/1e9:,.3f} B VND' if v is not None else 'N/A'
def clean(df):return df.copy() if not df.empty else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_all():
 out={}
 for key,path in P.items():
  try:out[key]=pd.read_csv(path,encoding='utf-8-sig') if path.exists() else pd.DataFrame()
  except Exception:out[key]=pd.DataFrame()
 return out

st.set_page_config(page_title='CM-TV | ECR Digital Twin',page_icon='🚢',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{padding-top:1.15rem;max-width:1500px} h1,h2,h3{letter-spacing:-.03em}
[data-testid="stMetric"]{background:#f0f5fa;border:1px solid #dce7f2;border-radius:13px;padding:12px 14px;min-height:108px}
[data-testid="stMetricValue"]{font-size:clamp(1.15rem,1.65vw,1.9rem)!important;white-space:normal!important}
[data-testid="stSidebar"]{background:#f1f5fa}
.portfolio-header{background:linear-gradient(110deg,#0b2542,#12517b);color:white;border-radius:18px;padding:22px 28px;margin-bottom:16px}
.portfolio-header h1{color:white;font-size:2rem;margin:0}.portfolio-header p{color:#d8e9f7;margin:8px 0 0}
.section-label{font-size:.76rem;letter-spacing:.13em;font-weight:800;color:#336c91;margin:12px 0 9px}
.note{padding:11px 14px;background:#edf6fc;border-left:4px solid #4b9aca;border-radius:7px;margin:9px 0}
</style>''',unsafe_allow_html=True)
D=load_all(); missing=[k for k in ['ops','kpi','routes','sensitivity','macro_summary'] if D[k].empty]

# Canonical normalized views: never manufacture numerical results if source columns are absent.
def normalize_routes(df):
 if df.empty:return pd.DataFrame()
 f=col(df,'From','From_Depot','Origin','From_Depot_ID','From_Node');t=col(df,'To','To_Depot','Destination','To_Depot_ID','To_Node');q=col(df,'Containers_Repositioned','Qty','Quantity','Total_Qty','Containers','Total_Containers','Repositioned_Containers');k=col(df,'Container_Type','Type');days=col(df,'Number_of_Move_Days','Move_Days','Days');cost=col(df,'Transport_Cost_VND','Total_Transport_Cost_VND','Total_Cost_VND','Cost_VND');km=col(df,'Road_km','Distance_km')
 if not all([f,t,q]):return pd.DataFrame()
 x=pd.DataFrame({'From':df[f].astype(str).str.strip(),'To':df[t].astype(str).str.strip(),'Qty':pd.to_numeric(df[q],errors='coerce').fillna(0)})
 x['Type']=df[k].astype(str) if k else 'All';x['Move_Days']=pd.to_numeric(df[days],errors='coerce') if days else float('nan');x['Cost']=pd.to_numeric(df[cost],errors='coerce') if cost else float('nan');x['Road_km']=pd.to_numeric(df[km],errors='coerce') if km else float('nan')
 x['From']=x['From'].replace(ALIASES);x['To']=x['To'].replace(ALIASES)
 return x[x.Qty>0]

R=normalize_routes(D['routes']); K=D['kpi']; M=D['macro_summary']; O=D['ops']; S=D['sensitivity']

def macro_row(scenario):
 c=col(M,'Scenario'); z=M[M[c].astype(str).str.upper()==scenario] if c else pd.DataFrame()
 return z.iloc[0] if len(z) else pd.Series(dtype=object)
def field(row,*names):
 for name in names:
  for key in row.index:
   if str(key).strip().lower()==name.lower():return number(row[key],None)
 return None

def dated(df):
 dc=col(df,'Date','Day');return pd.to_datetime(df[dc],errors='coerce') if dc else pd.Series(dtype='datetime64[ns]')

def plot_line(df,date_name,ys,title,height=300):
 fig=go.Figure()
 for c,label in ys:
  if c:fig.add_trace(go.Scatter(x=df[date_name],y=df[c],mode='lines',name=label,line={'width':2}))
 fig.update_layout(title=title,height=height,margin=dict(l=5,r=8,t=45,b=5),legend=dict(orientation='h',y=1.15),hovermode='x unified')
 return fig

# PDF is built only from loaded source data; no hardcoded KPI fallbacks.
def make_pdf(scenario):
 row=macro_row(scenario);bio=BytesIO();styles=getSampleStyleSheet()
 navy=colors.HexColor('#102c48');blue=colors.HexColor('#eaf2f8')
 styles.add(ParagraphStyle(name='CoverX',parent=styles['Title'],fontSize=21,leading=26,textColor=navy,spaceAfter=12))
 styles.add(ParagraphStyle(name='HeadX',parent=styles['Heading2'],fontSize=13,leading=17,textColor=navy,spaceBefore=15,spaceAfter=7))
 styles.add(ParagraphStyle(name='SmallX',parent=styles['Normal'],fontSize=8.4,leading=12))
 doc=SimpleDocTemplate(bio,pagesize=A4,leftMargin=19*mm,rightMargin=19*mm,topMargin=18*mm,bottomMargin=16*mm)
 story=[]
 def p(text,style='Normal'):story.append(Paragraph(html.escape(str(text)),styles[style]))
 def heading(text):p(text,'HeadX')
 def table(headers,rows,widths=None):
  if not rows: p('Source data not available.');return
  cells=[[Paragraph(html.escape(str(x)),styles['SmallX']) for x in headers]]+[[Paragraph(html.escape(str(x)),styles['SmallX']) for x in r] for r in rows]
  t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,blue]),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#ccd8e2'))]));story.append(t)
 p('CAI MEP - THI VAI','CoverX');p('EMPTY CONTAINER DIGITAL TWIN | PORTFOLIO REPORT','Heading2')
 p(f'Macro scenario: {scenario}   |   Generated: {datetime.now():%Y-%m-%d %H:%M}')
 story.append(Spacer(1,9*mm))
 p('Scope: three-terminal reference scale, calibrated depot planning scenarios, and an independent 90-day synthetic ECR optimization case. No observed daily depot inventory is claimed.','SmallX')
 heading('01 | Macro planning context - Step 08')
 table(['Terminal','Reference TEU/year'],[(r[1],integer(r[5])) for r in TERMINALS]+[('Combined reference',integer(sum(r[5] for r in TERMINALS)))],[95*mm,70*mm])
 story.append(Spacer(1,5*mm))
 table(['Scenario metric','Value'],[
 ('Relevant empty-flow ratio',f"{field(row,'Relevant_Empty_Ratio'):.0%}" if field(row,'Relevant_Empty_Ratio') is not None else 'N/A'),
 ('Estimated demand / 90 days',integer(field(row,'Total_Demand_90d'))),
 ('Estimated returns / 90 days',integer(field(row,'Total_Return_90d'))),
 ('Estimated baseline shortage',integer(field(row,'Baseline_Shortage_90d')))], [95*mm,70*mm])
 heading('02 | Depot planning allocation')
 table(['Depot','Planning share'],[(r[2],f'{r[5]:.0%}') for r in DEPOTS],[110*mm,55*mm]);p('Allocation shares are Step 08 assumptions, not measured terminal-to-depot routes.','SmallX')
 story.append(PageBreak());heading('03 | Geographic study network')
 table(['Node','Role','Latitude','Longitude'],[(r[0],'Terminal',f'{r[3]:.6f}',f'{r[4]:.6f}') for r in TERMINALS]+[(r[0],'Depot',f'{r[3]:.6f}',f'{r[4]:.6f}') for r in DEPOTS],[47*mm,35*mm,41*mm,41*mm]);p('Project reference/gate points selected from satellite mapping; not surveyed coordinates.','SmallX')
 heading('04 | Independent synthetic optimization - Steps 05/06')
 vals=[('Baseline shortage',metric(K,'Baseline_Shortage')),('Optimized shortage',metric(K,'Optimized_Shortage')),('Repositioned containers',metric(K,'Containers_Repositioned')),('Transport cost (VND)',metric(K,'ECR_Transport_Cost_VND')),('MILP objective (VND)',metric(K,'MILP_Objective_VND'))]
 table(['Optimization metric','Source result'],[(a,integer(b)) for a,b in vals],[95*mm,70*mm])
 heading('05 | Optimal ECR routes - Step 06')
 table(['Container','From','To','Qty'],[(r.Type,r['From'],r['To'],integer(r.Qty)) for _,r in R.iterrows()],[34*mm,53*mm,53*mm,25*mm])
 story.append(PageBreak());heading('06 | Sensitivity - Step 07')
 sc=col(S,'Scenario');sh=col(S,'Optimized_Shortage');qty=col(S,'Containers_Repositioned');ct=col(S,'ECR_Transport_Cost_VND')
 if all([sc,sh,qty,ct]):table(['Scenario','Shortage','ECR moves','Transport VND'],[(r[sc],integer(number(r[sh])),integer(number(r[qty])),integer(number(r[ct]))) for _,r in S.iterrows()],[56*mm,30*mm,34*mm,45*mm])
 else:p('Sensitivity file or required columns are unavailable.')
 heading('07 | Methodology and data confidence')
 table(['Layer','Classification'],[('Terminal throughput','Public reference / approximate'),('Coordinates','User-selected reference points'),('Road distance','Derived model input'),('Transport cost','Planning assumption'),('Step 08 empty flow / depot allocation','Calibrated scenario + assumptions'),('Step 05 90-day depot operations','Synthetic case study'),('Step 06 MILP decisions','Optimization on synthetic data'),('Step 07 sensitivity','Model experiment')],[98*mm,67*mm])
 p('IMPORTANT: Step 08 quantities and Step 05-07 quantities are not one continuous observed flow and must not be added or interpreted as actual terminal/depot operations.','SmallX')
 def page_num(canvas,document):
  canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(navy);canvas.drawString(19*mm,10*mm,'CM-TV ECR | Research prototype');canvas.drawRightString(193*mm,10*mm,f'Page {document.page}');canvas.restoreState()
 doc.build(story,onFirstPage=page_num,onLaterPages=page_num);return bio.getvalue()

st.sidebar.markdown('## 🚢 ECR CONTROL CENTER')
scenario=st.sidebar.radio('MACRO SCENARIO',['LOW','BASE','HIGH'],index=1,horizontal=True)
page=st.sidebar.radio('EXPLORE',['01  Executive overview','02  Macro & depot planning','03  Geographic network','04  Synthetic operations','05  MILP optimization','06  ECR route map','07  Sensitivity','08  Data & methodology','09  PDF & LinkedIn'],label_visibility='visible')
st.sidebar.divider();st.sidebar.caption('STEP 08: calibrated planning scale');st.sidebar.caption('STEPS 05-07: independent synthetic optimization')

st.markdown('<div class="portfolio-header"><h1>CAI MEP - THI VAI | ECR DIGITAL TWIN</h1><p>Three-terminal planning context · Six-node network · 90-day synthetic MILP optimization</p></div>',unsafe_allow_html=True)
if missing:st.warning('Missing/empty source files: '+', '.join(missing)+'. Affected results will show N/A rather than invented values.')
# PDF download prominently on every page, and also on dedicated report page.
try:
 pdf=make_pdf(scenario)
 st.download_button(f'📄 Download {scenario} portfolio PDF',pdf,file_name=f'CM_TV_ECR_Portfolio_{scenario}.pdf',mime='application/pdf',type='primary',key='top_pdf')
except Exception as exc:
 st.error(f'PDF generation failed: {exc}');pdf=None

mr=macro_row(scenario);m_demand=field(mr,'Total_Demand_90d');m_return=field(mr,'Total_Return_90d');m_short=field(mr,'Baseline_Shortage_90d');m_ratio=field(mr,'Relevant_Empty_Ratio')
base=metric(K,'Baseline_Shortage');opt=metric(K,'Optimized_Shortage');moves=metric(K,'Containers_Repositioned');cost=metric(K,'ECR_Transport_Cost_VND')

def kpis(items):
 cs=st.columns(len(items))
 for c,(name,val) in zip(cs,items):c.metric(name,val)

def route_map(draw_routes=False):
 m=folium.Map(location=[10.517,107.033],zoom_start=12,tiles='OpenStreetMap',control_scale=True)
 terminals=folium.FeatureGroup(name='Terminals',show=True);depots=folium.FeatureGroup(name='Depots',show=True);arrows=folium.FeatureGroup(name='Synthetic MILP ECR routes',show=draw_routes)
 for r in TERMINALS:folium.Marker([r[3],r[4]],tooltip=f'{r[0]} | {r[1]}',popup=f'{r[2]}<br>Reference: {r[5]:,} TEU/year',icon=folium.Icon(color='blue',icon='ship',prefix='fa')).add_to(terminals)
 for r in DEPOTS:folium.Marker([r[3],r[4]],tooltip=f'{r[0]} | {r[1]}',popup=f'{r[2]}<br>Planning share: {r[5]:.0%}',icon=folium.Icon(color='green',icon='industry',prefix='fa')).add_to(depots)
 if draw_routes and not R.empty:
  palette={'20GP':'#0891b2','40GP':'#ea580c','40HC':'#8b5cf6'}
  for _,r in R.iterrows():
   if r['From'] not in COORD or r['To'] not in COORD:continue
   a=COORD[r['From']];b=COORD[r['To']];color=palette.get(str(r.Type),'#334155')
   # Straight connection is conceptual; actual road distances are from Step 02.
   popup=(f"<b>{r['From']} → {r['To']}</b><br>Container: {r.Type}<br>Quantity: {integer(r.Qty)}<br>Road distance: {number(r.Road_km):.2f} km<br>Move days: {integer(r.Move_Days)}<br>Transport cost: {integer(r.Cost)} VND")
   AntPath([a,b],color=color,weight=min(11,max(3,number(r.Qty)/65)),delay=900,dash_array=[10,15],tooltip=f"{r['From']} → {r['To']} | {r.Type} | {integer(r.Qty)} units",popup=folium.Popup(popup,max_width=330)).add_to(arrows)
 terminals.add_to(m);depots.add_to(m)
 if draw_routes:arrows.add_to(m)
 folium.LayerControl(collapsed=False).add_to(m)
 st_folium(m,height=460,use_container_width=True,returned_objects=[])
 st.caption('Markers use project reference coordinates. ECR arrows show MILP origin/destination, not surveyed road alignments.')

if page.startswith('01'):
 st.markdown('<div class="section-label">A · MACRO PLANNING / STEP 08</div>',unsafe_allow_html=True)
 kpis([('CMIT','1.10M TEU/yr'),('TCIT','2.248M TEU/yr'),('SSIT','~1.00M TEU/yr'),('3-terminal reference','4.348M TEU/yr')])
 st.markdown('<div class="section-label">CALIBRATED SCENARIO · '+scenario+'</div>',unsafe_allow_html=True)
 kpis([('Empty flow assumption',f'{m_ratio:.0%}' if m_ratio is not None else 'N/A'),('Demand / 90d',integer(m_demand)),('Return / 90d',integer(m_return)),('Scenario shortage',integer(m_short))])
 st.markdown('<div class="note">Macro reference pool → empty-flow assumption → depot planning shares: D01 35% · D02 35% · D03 30%. Shares are not observed terminal-to-depot shipments.</div>',unsafe_allow_html=True)
 st.divider();st.markdown('<div class="section-label">B · INDEPENDENT 90-DAY SYNTHETIC CASE / STEPS 05-07</div>',unsafe_allow_html=True)
 reduction=(base-opt)/base*100 if base and opt is not None else None
 kpis([('Before ECR',integer(base)),('MILP ECR moves',integer(moves)),('After ECR',integer(opt)),('Shortage reduction',f'{reduction:.1f}%' if reduction is not None else 'N/A'),('Transport cost',money(cost))])
 left,right=st.columns([1,1])
 with left:
  if base is not None and opt is not None:
   fig=px.bar(pd.DataFrame({'Stage':['Before MILP','After MILP'],'Shortage':[base,opt]}),x='Stage',y='Shortage',text='Shortage',title='Synthetic shortage: before vs after',color='Stage');fig.update_layout(height=285,showlegend=False,margin=dict(l=0,r=5,t=45,b=0));st.plotly_chart(fig,use_container_width=True)
 with right:
  if not R.empty:
   fig=px.bar(R,x='Type',y='Qty',color='From',title='Optimal repositioning by container type',barmode='stack');fig.update_layout(height=285,margin=dict(l=0,r=5,t=45,b=0));st.plotly_chart(fig,use_container_width=True)
 st.caption('Step 08 scenario and Step 05-07 experiment are independent datasets; results must not be summed.')

elif page.startswith('02'):
 st.subheader('Macro scale → depot planning')
 fig=px.pie(pd.DataFrame({'Terminal':[r[1] for r in TERMINALS],'TEU':[r[5] for r in TERMINALS]}),names='Terminal',values='TEU',hole=.55,title='Three-terminal reference throughput')
 a,b=st.columns(2)
 with a:st.plotly_chart(fig,use_container_width=True)
 with b:
  fig=px.bar(pd.DataFrame({'Depot':[r[1] for r in DEPOTS],'Share':[r[5]*100 for r in DEPOTS]}),x='Depot',y='Share',text='Share',title='Step 08 assumed depot allocation');fig.update_layout(yaxis_title='Share (%)');st.plotly_chart(fig,use_container_width=True)
 x=D['macro_'+scenario];dc=col(x,'Date');rc=col(x,'Empty_Return','Return');dem=col(x,'Total_Demand','Demand')
 if all([dc,rc,dem]):
  z=x.groupby(dc,as_index=False)[[rc,dem]].sum();st.plotly_chart(plot_line(z,dc,[(rc,'Return'),(dem,'Demand')],'Estimated daily flow (Step 08)'),use_container_width=True)
 s=D['macro_depots'];sc=col(s,'Scenario');de=col(s,'Depot_ID');ty=col(s,'Container_Type');nf=col(s,'Net_Flow')
 if all([sc,de,ty,nf]):
  x=s[s[sc].astype(str).str.upper()==scenario];heat=x.pivot_table(index=de,columns=ty,values=nf,aggfunc='sum');st.plotly_chart(px.imshow(heat,text_auto=True,aspect='auto',title='Calibrated scenario: return − demand'),use_container_width=True)
 st.info('Public throughput is a calibration reference. Empty-flow ratios and depot allocations are assumptions, not measured operating statistics.')

elif page.startswith('03'):
 st.subheader('Six-node geographic network');route_map(False)
 st.dataframe(pd.DataFrame([{'Node':r[0],'Facility':r[2],'Lat':r[3],'Lon':r[4],'Role':'Terminal' if len(r)>5 and isinstance(r[5],int) else 'Depot'} for r in TERMINALS+DEPOTS]),hide_index=True,use_container_width=True)
 if not D['road'].empty:
  st.subheader('Step 02 road reference');st.dataframe(D['road'],hide_index=True,use_container_width=True)

elif page.startswith('04'):
 st.subheader('Synthetic 90-day depot operations · Step 05')
 if not O.empty:
  depot=col(O,'Depot_ID');typ=col(O,'Container_Type');dt=col(O,'Date');ret=col(O,'Empty_Return');dem=col(O,'Total_Demand');sho=col(O,'Shortage');closing=col(O,'Closing_Available')
  if all([depot,typ,dt,ret,dem]):
   a,b=st.columns(2);d=a.selectbox('Depot',sorted(O[depot].dropna().unique()));t=b.selectbox('Container type',sorted(O[typ].dropna().unique()));x=O[(O[depot]==d)&(O[typ]==t)].sort_values(dt)
   kpis([('Return / 90d',integer(x[ret].sum())),('Demand / 90d',integer(x[dem].sum())),('Shortage / 90d',integer(x[sho].sum()) if sho else 'N/A'),('Mean closing stock',integer(x[closing].mean()) if closing else 'N/A')]);st.plotly_chart(plot_line(x,dt,[(ret,'Return'),(dem,'Demand'),(closing,'Closing inventory')],'Daily synthetic operations',390),use_container_width=True)
  summ=D['ops_summary'];de=col(summ,'Depot_ID');ty=col(summ,'Container_Type');nf=col(summ,'Net_Flow')
  if all([de,ty,nf]):st.plotly_chart(px.imshow(summ.pivot_table(index=de,columns=ty,values=nf),text_auto=True,aspect='auto',title='90-day synthetic spatial imbalance'),use_container_width=True)
 else:st.error('Step 05 operational CSV not found.')

elif page.startswith('05'):
 st.subheader('Multi-period MILP optimization · Step 06')
 kpis([('Baseline shortage',integer(base)),('After optimization',integer(opt)),('Repositioned',integer(moves)),('Transport cost',money(cost))]);st.caption('MILP objective also includes other modeled terms; it is not the transport cost.')
 if not R.empty:
  st.dataframe(R,hide_index=True,use_container_width=True)
  st.plotly_chart(px.bar(R,x='From',y='Qty',color='Type',facet_col='To',title='Optimal route quantities'),use_container_width=True)
 if not D['daily_kpi'].empty:
  st.subheader('Daily optimization KPIs');st.dataframe(D['daily_kpi'],hide_index=True,use_container_width=True)

elif page.startswith('06'):
 st.subheader('Optimal ECR network · Step 06 synthetic case')
 route_count=len(R) if not R.empty else 0
 route_qty=R['Qty'].sum() if not R.empty else 0
 route_cost=R['Cost'].sum() if not R.empty else 0
 reduction=(base-opt)/base*100 if base and opt is not None else None
 kpis([('Optimal routes',integer(route_count)),('Repositioned',integer(route_qty)),('Transport cost',money(route_cost)),('Shortage eliminated',f'{reduction:.1f}%' if reduction is not None else 'N/A')])
 route_map(True)
 if not R.empty:
  show=R[['Type','From','To','Qty','Move_Days','Road_km','Cost']].copy()
  show.columns=['Container Type','From Depot','To Depot','Containers Repositioned','Move Days','Road km','Transport Cost VND']
  st.subheader('Optimal route summary')
  st.dataframe(show,hide_index=True,use_container_width=True)
  fig=px.bar(R,x='Qty',y=R['From']+' → '+R['To'],color='Type',orientation='h',text='Qty',title='Repositioned containers by optimal route')
  fig.update_layout(height=330,yaxis_title='Route',xaxis_title='Containers repositioned',margin=dict(l=5,r=5,t=45,b=5))
  st.plotly_chart(fig,use_container_width=True)
  st.caption('Map lines show MILP origin/destination only. Road km and transport cost come from the Step 02/03 model inputs; the straight map lines are not surveyed road alignments.')
 else:st.warning('Cannot plot routes: Step 06 route-summary CSV is missing or required columns are not recognized.')

elif page.startswith('07'):
 st.subheader('Sensitivity analysis · Step 07')
 if not S.empty:
  sc=col(S,'Scenario');sh=col(S,'Optimized_Shortage');qty=col(S,'Containers_Repositioned');ct=col(S,'ECR_Transport_Cost_VND')
  if sc:
   a,b=st.columns(2)
   if sh:a.plotly_chart(px.bar(S,x=sc,y=sh,text_auto='.0f',title='Remaining shortage by scenario'),use_container_width=True)
   if qty:b.plotly_chart(px.bar(S,x=sc,y=qty,text_auto='.0f',title='Repositioned containers'),use_container_width=True)
   if ct:st.plotly_chart(px.bar(S,x=sc,y=ct,title='Transport-cost sensitivity'),use_container_width=True)
  st.dataframe(S,hide_index=True,use_container_width=True)
 else:st.warning('Step 07 sensitivity summary not found.')

elif page.startswith('08'):
 st.subheader('Methodology & data confidence')
 st.markdown('**Macro:** Three-terminal public reference → LOW/BASE/HIGH empty-flow assumptions → D01/D02/D03 planning allocation. **Micro:** independent synthetic 90-day inventory → road cost → MILP → sensitivity.')
 classification=pd.DataFrame([('Terminal throughput','PUBLIC REFERENCE / APPROXIMATE'),('Six node positions','USER-SELECTED REFERENCE'),('Road distances','DERIVED NETWORK INPUT'),('Transport tariffs','PLANNING ASSUMPTION'),('Step 08 empty ratio and depot shares','CALIBRATION ASSUMPTION'),('Step 08 daily flow','CALIBRATED SCENARIO'),('Step 05 depot stock / demand','SYNTHETIC'),('Step 06 routes / costs','OPTIMIZATION RESULT ON SYNTHETIC DATA'),('Step 07 sensitivity','MODEL EXPERIMENT')],columns=['Data layer','Classification']);st.dataframe(classification,hide_index=True,use_container_width=True)
 for label,key in [('Step 08 public references','public'),('Step 08 calibration assumptions','assumptions')]:
  if not D[key].empty:
   with st.expander(label):st.dataframe(D[key],hide_index=True,use_container_width=True)
 st.warning('The dashboard is a research decision-support prototype. It does not claim actual depot inventory or actual optimal routing for CM-TV.')

elif page.startswith('09'):
 st.subheader('Export & LinkedIn portfolio')
 if pdf:st.download_button('📄 Download full portfolio PDF',pdf,file_name=f'CM_TV_ECR_Portfolio_{scenario}.pdf',mime='application/pdf',type='primary',key='page_pdf')
 st.markdown('**Suggested LinkedIn project title:** Empty Container Digital Twin & Repositioning Optimization — Cai Mep–Thi Vai')
 st.markdown('**Recommended screenshots:** Executive overview, six-node map, optimal ECR network, and sensitivity analysis. Keep the synthetic-data qualification visible.')
 st.markdown('**Suggested project description:**')
 st.code('Developed a research prototype combining public-scale terminal throughput references, calibrated empty-container planning scenarios, a six-node geographic network, and an independent 90-day synthetic MILP repositioning case. Interactive dashboard and PDF reporting built with Python, Streamlit, Plotly, Folium and ReportLab. The operational case is simulated, not observed depot data.',language=None)
 st.link_button('Open LinkedIn profile','https://www.linkedin.com/in/minh-nguyen-53830b3b8/')

st.divider();st.caption('CM-TV ECR | Step 09.V2.1 Portfolio Edition | Public-scale planning ≠ independent synthetic optimization')
