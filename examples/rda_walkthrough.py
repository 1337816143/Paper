"""Complete SYNTHETIC two-response/two-predictor RDA teaching calculations.

Python standard library only. Not Cheng2023 data or a reproduction of Fig7.
The four invented village rows illustrate arithmetic, never a sample-size rule.
X and Y are column-standardized with sample SD. Fitted-axis scores are Yhat V.
Variable plotting coordinates are corr(variable, fitted-axis score), not an
assertion about vegan's or the paper's unknown plotting scaling. Missing axis
correlations stay null, never fabricated zero. No permutation inference is made.
"""
import argparse,csv,json,math,statistics
from pathlib import Path
DATA=Path(__file__).with_name('rda_synthetic_villages.csv')
COLUMNS=['crop_share_percent','distance_km','perception_a','perception_b']
TOL=1e-12

def transpose(a):return [list(c) for c in zip(*a)]
def multiply(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in transpose(b)] for row in a]
def correlation(a,b):
 am,bm=statistics.mean(a),statistics.mean(b);ac=[x-am for x in a];bc=[x-bm for x in b];den=math.sqrt(sum(x*x for x in ac)*sum(x*x for x in bc))
 return max(-1,min(1,sum(x*y for x,y in zip(ac,bc))/den)) if den>TOL else None

def standardize(a):
 cols=transpose(a);means=[statistics.mean(c) for c in cols];sds=[statistics.stdev(c) for c in cols]
 if min(sds)<=TOL:raise ValueError('A constant column cannot be standardized')
 return [[(v-means[j])/sds[j] for j,v in enumerate(row)] for row in a],means,sds

def read_records(path=DATA):
 with Path(path).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))

def eigen_2x2(a):
 x,y=a[0];_,z=a[1];delta=math.hypot(x-z,2*y);values=[(x+z+delta)/2,(x+z-delta)/2]
 if min(values)<-1e-10:raise ValueError('Fitted covariance is not positive semidefinite')
 values=[max(0,v) for v in values]
 if abs(y)<=TOL:v=[1.,0.] if x>=z else [0.,1.]
 else:
  options=[[y,values[0]-x],[values[0]-z,y]];v=max(options,key=lambda r:sum(q*q for q in r));norm=math.hypot(*v);v=[q/norm for q in v]
 second=[-v[1],v[0]];vectors=[v,second]
 for row in vectors:
  k=max(range(2),key=lambda i:abs(row[i]))
  if row[k]<0:row[:]=[-q for q in row]
 return values,transpose(vectors)

def calculate(records=None,v4_b=None):
 records=read_records() if records is None else records
 if len(records)<4:raise ValueError('At least four complete teaching rows are required')
 ids=[];matrix=[]
 for raw in records:
  id=raw.get('village_id')
  if not id or id in ids:raise ValueError('Village IDs must be present and unique')
  ids.append(id);row=[]
  for key in COLUMNS:
   try:v=float(raw[key])
   except (KeyError,TypeError,ValueError) as e:raise ValueError('Missing or non-numeric '+key) from e
   if not math.isfinite(v):raise ValueError('Non-finite '+key)
   row.append(v)
  matrix.append(row)
 if v4_b is not None:
  if not isinstance(v4_b,(int,float)) or not math.isfinite(v4_b) or not 0<=v4_b<=5:raise ValueError('Synthetic V4-B must be finite within0..5')
  if 'V4' not in ids:raise ValueError('No V4 row')
  matrix[ids.index('V4')][3]=v4_b
 x=[r[:2] for r in matrix];y=[r[2:] for r in matrix];xs,xmean,xsd=standardize(x);ys,ymean,ysd=standardize(y);n=len(ids)
 xx=multiply(transpose(xs),xs);xy=multiply(transpose(xs),ys);a,b=xx[0];c,d=xx[1];det=a*d-b*c
 if abs(det)<TOL:raise ValueError('Predictors are collinear; XTX cannot be inverted')
 inverse=[[d/det,-b/det],[-c/det,a/det]];coefficients=multiply(inverse,xy);fit=multiply(xs,coefficients)
 residual=[[ys[i][j]-fit[i][j] for j in range(2)] for i in range(n)]
 fit_raw=[[fit[i][j]*ysd[j]+ymean[j] for j in range(2)] for i in range(n)]
 residual_raw=[[y[i][j]-fit_raw[i][j] for j in range(2)] for i in range(n)]
 inertia=lambda m:sum(v*v for row in m for v in row)/(n-1)
 total,constrained,unconstrained=[inertia(m) for m in [ys,fit,residual]]
 covariance=[[v/(n-1) for v in row] for row in multiply(transpose(fit),fit)]
 eigenvalues,vectors=eigen_2x2(covariance);axes=multiply(fit,vectors);observed_axes=multiply(ys,vectors)
 xcoords=[[correlation(col,axis) for axis in transpose(axes)] for col in transpose(xs)]
 ycoords=[[correlation(col,axis) for axis in transpose(axes)] for col in transpose(ys)]
 def cosine(a,b):
  if None in a or None in b:return None
  den=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
  return sum(x*y for x,y in zip(a,b))/den if den>TOL else None
 return {'scope':'SYNTHETIC four-village RDA mechanism; no author data, plot scaling or causal reproduction',
         'row_ids':ids,'raw_matrix':matrix,'X':x,'Y':y,'X_means':xmean,'X_sample_sd':xsd,'Y_means':ymean,'Y_sample_sd':ysd,
         'X_standardized':xs,'Y_standardized':ys,'XTX':xx,'XTY':xy,'XTX_inverse':inverse,'coefficients':coefficients,
         'fitted_Y':fit,'residual_Y':residual,'fitted_Y_original_units':fit_raw,'residual_Y_original_units':residual_raw,
         'XT_residual':multiply(transpose(xs),residual),'fitted_covariance':covariance,'constrained_eigenvalues':eigenvalues,
         'eigenvectors_columns':vectors,'fitted_axis_scores':axes,'observed_axis_scores':observed_axes,
         'X_axis_correlations':xcoords,'Y_axis_correlations':ycoords,'Y_raw_correlation':correlation([r[0] for r in y],[r[1] for r in y]),
         'Y_coordinate_cosine':cosine(ycoords[0],ycoords[1]),'X1_YA_raw_correlation':correlation([r[0] for r in x],[r[0] for r in y]),
         'X1_YA_coordinate_cosine':cosine(xcoords[0],ycoords[0]),'total_inertia':total,'constrained_inertia':constrained,
         'residual_inertia':unconstrained,'overall_unadjusted_R2':constrained/total,'residual_fraction':unconstrained/total,
         'axis_fraction_of_TOTAL':[v/total for v in eigenvalues],
         'axis_fraction_of_CONSTRAINED':[v/constrained for v in eigenvalues] if constrained>TOL else None,
         'axis_defined':[v>TOL for v in eigenvalues],'residual_degrees_of_freedom':n-3}

def test():
 r=calculate();near=lambda a,b:math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)
 assert r['X_means']==[20,4] and r['Y_means']==[3,3]
 assert near(r['X_standardized'][0][0],-math.sqrt(3)/2)
 assert near(r['Y_standardized'][0][0],-1/math.sqrt(2))
 assert near(r['fitted_Y'][0][0],-3/(2*math.sqrt(2))) and near(r['residual_Y'][0][0],1/(2*math.sqrt(2)))
 assert near(r['fitted_Y_original_units'][0][0],1.5) and near(r['residual_Y_original_units'][0][0],.5)
 assert near(r['total_inertia'],2) and near(r['constrained_inertia'],25/18) and near(r['residual_inertia'],11/18)
 assert all(near(a,b) for a,b in zip(r['constrained_eigenvalues'],[5/6,5/9]))
 assert all(near(a,b) for a,b in zip(r['axis_fraction_of_TOTAL'],[5/12,5/18]))
 assert all(near(a,b) for a,b in zip(r['axis_fraction_of_CONSTRAINED'],[.6,.4]))
 assert near(r['Y_raw_correlation'],math.sqrt(2/27)) and near(r['Y_coordinate_cosine'],0)
 assert near(r['X1_YA_raw_correlation'],math.sqrt(2/3)) and near(r['X1_YA_coordinate_cosine'],2/math.sqrt(5))
 dynamic=calculate(v4_b=4.25)
 assert abs(dynamic['fitted_covariance'][0][1])>.01
 assert not near(dynamic['eigenvectors_columns'][0][1],0)
 assert near(dynamic['constrained_eigenvalues'][0],137/204+math.sqrt(257)/68) and near(dynamic['constrained_eigenvalues'][1],137/204-math.sqrt(257)/68)
 for v in [r,dynamic,calculate(list(reversed(read_records())))]:
  assert near(v['total_inertia'],v['constrained_inertia']+v['residual_inertia'])
  assert all(abs(q)<1e-10 for row in v['XT_residual'] for q in row)
  assert near(sum(v['constrained_eigenvalues']),v['constrained_inertia'])
  product=multiply(v['fitted_covariance'],v['eigenvectors_columns'])
  assert all(near(product[i][j],v['eigenvectors_columns'][i][j]*v['constrained_eigenvalues'][j]) for i in range(2) for j in range(2))
 base=read_records();rankone=[dict(row,perception_b=row['perception_a']) for row in base];one=calculate(rankone)
 assert one['axis_defined']==[True,False] and all(row[1] is None for row in one['Y_axis_correlations'])
 for bad in [[dict(row,distance_km=float(row['crop_share_percent'])*2) for row in base],[dict(row,distance_km=1) for row in base],base+[base[0]],[dict(row,perception_a='') for row in base]]:
  try:calculate(bad)
  except ValueError:pass
  else:raise AssertionError('Invalid matrix accepted')
 for bad in ['',float('nan'),float('inf'),-1,6]:
  try:calculate(v4_b=bad)
  except ValueError:pass
  else:raise AssertionError('Invalid synthetic input accepted')
 json.dumps(r,allow_nan=False);json.dumps(dynamic,allow_nan=False);json.dumps(one,allow_nan=False)
 return {'passed':True,'scope':'Synthetic standardized regression, residual decomposition, dynamic eigensystem/correlations, undefined-axis and input guards; no author/R parity or browser claim'}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,default=DATA);p.add_argument('--v4-b',type=float);p.add_argument('--test',action='store_true');a=p.parse_args()
 print(json.dumps(test() if a.test else calculate(read_records(a.input),a.v4_b),ensure_ascii=False,indent=2,allow_nan=False))
