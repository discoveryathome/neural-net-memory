// Fixed-first-forward-order dynamic rematerialization search.
// General exhaustion concerns that domain. This package proves the pinned
// first-final-GELU favorable tail covers every global 12-unit trace, and checks its
// complete finite closure with a separately authored Python implementation.
// All resident inputs count; outputs allocate before evictions after execution.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <queue>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <sys/resource.h>
#include <stdexcept>
#include <array>
#include <iomanip>
using U=uint64_t;
struct Key { U lp,done; bool operator==(const Key&o)const{return lp==o.lp&&done==o.done;} };
struct Hash { size_t operator()(const Key&k)const { U x=k.lp^(k.done+0x9e3779b97f4a7c15ULL+(k.lp<<6)+(k.lp>>2));x^=x>>30;x*=0xbf58476d1ce4e5b9ULL;x^=x>>27;x*=0x94d049bb133111ebULL;return x^(x>>31);} };
struct Rec { Key key;U cost,gone;uint32_t parent;uint8_t node; };
struct Label {U cost;uint32_t id;};
struct Q {double f; U cost;uint32_t id;int progress;bool operator<(const Q&o)const {if(f!=o.f)return f>o.f;if(progress!=o.progress)return progress<o.progress;if(cost!=o.cost)return cost<o.cost;return id>o.id;}};
struct Node{std::string name;int size;U cost,dep,req,children;bool repeat;};
int main(int argc,char**argv){
 std::cout<<std::setprecision(17);
 if(argc<2||argc>7)return 2;std::ifstream in(argv[1]);int n,fixed,cap;U budget,maxrecords;double seconds,weight;
 int demandmode;in>>n>>fixed>>cap>>budget>>maxrecords>>seconds>>weight>>demandmode;
 if(n<1||n>56||fixed<0||cap<fixed||!std::isfinite(seconds)||seconds<=0||!std::isfinite(weight)||weight<0){std::cout<<"{\"status\":\"INVALID\"}\n";return 2;}
 std::vector<Node> ns(n);for(auto&v:ns){int rep;in>>v.name>>v.size>>v.cost>>v.dep>>v.req>>v.children>>rep;v.repeat=rep;}
 std::vector<int> order(n);for(auto&x:order)in>>x;U outputs;in>>outputs;int seedcount;in>>seedcount;
 struct Seed{U live,done,cost;int m;};std::vector<Seed> seeds(seedcount);
 for(auto&s:seeds)in>>s.live>>s.done>>s.m>>s.cost;
 int pdbrows,pdbwidth;U pdbunit;in>>pdbrows>>pdbwidth>>pdbunit;
 std::vector<int> pdbdi(16384,-1);std::vector<uint32_t> pdb;
 if(pdbrows){if(argc<3||pdbwidth!=4096||n%14)throw std::runtime_error("invalid PDB header");for(int row=0;row<pdbrows;row++){int mask;in>>mask;if(mask<0||mask>=16384)throw std::runtime_error("invalid PDB done mask");pdbdi[mask]=row;}pdb.resize(pdbrows*pdbwidth);std::ifstream data(argv[2],std::ios::binary);data.read(reinterpret_cast<char*>(pdb.data()),pdb.size()*4);if(data.gcount()!=int(pdb.size()*4))throw std::runtime_error("incomplete PDB");}
 int demandwidth=0;U demandunit=0;in>>demandwidth>>demandunit;std::vector<uint32_t> demandpdb;
 if(demandwidth){if(argc<4||!pdbrows||demandwidth!=16384)throw std::runtime_error("invalid demand PDB header");demandpdb.resize(demandwidth);std::ifstream data(argv[3],std::ios::binary);data.read(reinterpret_cast<char*>(demandpdb.data()),demandwidth*4);if(data.gcount()!=demandwidth*4)throw std::runtime_error("incomplete demand PDB");}
 int terminalwidth=0;U terminalunit=0;in>>terminalwidth>>terminalunit;std::vector<uint32_t> terminalpdb;
 if(terminalwidth){if(argc<5||!pdbrows||terminalwidth!=8192)throw std::runtime_error("invalid terminal PDB header");terminalpdb.resize(2*terminalwidth);std::ifstream data(argv[4],std::ios::binary);data.read(reinterpret_cast<char*>(terminalpdb.data()),terminalpdb.size()*4);if(data.gcount()!=int(terminalpdb.size()*4))throw std::runtime_error("incomplete terminal PDB");}
 int regionmode=0;in>>regionmode;
 std::array<std::vector<uint32_t>,4> regionback,regionterminal;
 if(regionmode){
  if(argc<6||n!=56||fixed!=1||cap!=12||!pdbrows||!demandwidth||!terminalwidth)throw std::runtime_error("invalid region-bound domain");
  regionback[3]=pdb;regionterminal[3]=terminalpdb;
  for(int c=9;c<12;c++){
   regionback[c-9].resize(pdb.size());regionterminal[c-9].resize(terminalpdb.size());
   std::ifstream b(std::string(argv[5])+"/b4-backward-pdb-cap"+std::to_string(c)+".bin",std::ios::binary);b.read(reinterpret_cast<char*>(regionback[c-9].data()),pdb.size()*4);if(b.gcount()!=int(pdb.size()*4))throw std::runtime_error("incomplete lower-cap backward table");
   std::ifstream t(std::string(argv[5])+"/b4-terminal-phase-pdb-cap"+std::to_string(c)+".bin",std::ios::binary);t.read(reinterpret_cast<char*>(regionterminal[c-9].data()),terminalpdb.size()*4);if(t.gcount()!=int(terminalpdb.size()*4))throw std::runtime_error("incomplete lower-cap terminal table");
  }
 }
 std::array<U,12> regionE;regionE.fill(budget+1);
 if(regionmode){
  std::vector<int> owned(16384);
  for(int live=1;live<16384;live++){int bit=live&-live;owned[live]=owned[live^bit]+ns[__builtin_ctz(unsigned(bit))].size;}
  for(int live=0;live<16384;live++)if(owned[live]<12&&demandpdb[live]!=UINT32_MAX)regionE[owned[live]]=std::min(regionE[owned[live]],U(demandpdb[live])*demandunit);
  for(int m=1;m<12;m++)regionE[m]=std::min(regionE[m],regionE[m-1]);
 }
 std::vector<U> prefix(n+1);for(int i=0;i<n;i++)prefix[i+1]=prefix[i]|(1ULL<<order[i]);
 U full=(1ULL<<n)-1,small=0,big=0,forbidden=0;
 for(int i=0;i<n;i++){if(ns[i].size==1)small|=1ULL<<i;else if(ns[i].size==4)big|=1ULL<<i;if(!ns[i].repeat)forbidden|=1ULL<<i;}
 bool simple=(small|big)==full;auto memory=[&](U m){if(simple)return fixed+__builtin_popcountll(m&small)+4*__builtin_popcountll(m&big);int z=fixed;while(m){int i=__builtin_ctzll(m);m&=m-1;z+=ns[i].size;}return z;};
 auto liveof=[&](Key k){return k.lp&full;};auto progress=[&](Key k){return int(k.lp>>56);};auto make=[&](U live,U done,int m){return Key{live|(U(m)<<56),done};};
 std::vector<U> ancestor(n);for(int i=0;i<n;i++){U a=(1ULL<<i)|ns[i].dep,t=ns[i].dep;while(t){int j=__builtin_ctzll(t);t&=t-1;a|=ancestor[j];}ancestor[i]=a;}
 std::unordered_map<U,std::pair<U,U>> needcache;
 auto needs=[&](U done){auto at=needcache.find(done);if(at!=needcache.end())return at->second;U req=0,useful=0;for(int i=0;i<n;i++)if(!(done>>i&1))req|=ns[i].req;U t=req;while(t){int j=__builtin_ctzll(t);t&=t-1;useful|=ancestor[j];}return needcache.emplace(done,std::make_pair(req,useful)).first->second;};
 auto normalize=[&](Key k){U live=liveof(k),done=k.done;int m=progress(k);if(m==n&&(live&outputs)==outputs)m=n+1;if(m==n+1){for(int i=n-1;i>=0;i--)if(!(done>>i&1)&&(done&ns[i].children)==ns[i].children&&(live&ns[i].req)==ns[i].req)done|=1ULL<<i;live&=needs(done).second;}return make(live,done,m);};
 auto heuristic=[&](Key k){
  U live=liveof(k);int m=progress(k);U seen=prefix[std::min(m,n)],required=needs(k.done).first;
  if(m<=n)required|=(full^seen)|outputs;
  U missing=0,todo=required&~live;
  while(todo){int i=__builtin_ctzll(todo);U bit=1ULL<<i;todo&=todo-1;if(missing&bit)continue;missing|=bit;todo|=ns[i].dep&~live&~missing;}
  U repeat=missing&seen;if(repeat&forbidden)return budget+1;
  U h=0,r=repeat;while(r){int i=__builtin_ctzll(r);r&=r-1;h+=ns[i].cost;}
  if(pdbrows){
   U sum=0;std::array<U,4> blockbounds{};
   for(int block=0;block<n/14;block++){
    int shift=block*14;U own12=4095ULL<<shift,own14=16383ULL<<shift;
    int localdone=(k.done>>shift)&16383;
    U owncost=0,outsidecost=0,bits=repeat&own14;
    while(bits){int i=__builtin_ctzll(bits);bits&=bits-1;owncost+=ns[i].cost;if(!(own12>>i&1))outsidecost+=ns[i].cost;}
    U localbound=owncost;
    if((seen&own12)==own12){
     int row=pdbdi[localdone];if(row<0)throw std::runtime_error("nonideal PDB projection");
     uint32_t value=pdb[row*pdbwidth+((live>>shift)&4095)];if(value==UINT32_MAX)return budget+1;
     localbound=std::max(localbound,U(value)*pdbunit+outsidecost);
    }
    if(demandwidth&&block+1<n/14&&(seen&own14)==own14&&localdone==0&&!(k.done>>(shift+14)&1)){
     uint32_t value=demandpdb[(live>>shift)&16383];if(value==UINT32_MAX)return budget+1;
     localbound=std::max(localbound,U(value)*demandunit);
    }
    if(terminalwidth&&block+1==n/14&&m<=n&&localdone==0&&(seen&own12)==own12&&!(seen>>(shift+13)&1)){
     int phase=int((seen>>(shift+12))&1);uint32_t value=terminalpdb[phase*terminalwidth+((live>>shift)&8191)];if(value==UINT32_MAX)return budget+1;
     localbound=std::max(localbound,U(value)*terminalunit);
    }
    blockbounds[block]=localbound;sum+=localbound;
   }
   h=std::max(h,sum);
   // Region minima stop before the highest unfinished block's norm1 read.
   // At its own minimum m, each earlier region still owes an output read;
   // its future owned work is >=E(m). All three minima reserve simultaneous
   // capacity for the complete final-block projection, despite identity transfers.
   int active=3;while(active>=0&&((k.done>>(14*active))&16383)==16383)active--;
   int targetshift=14*std::max(active,0);U earlier=(1ULL<<targetshift)-1,target12=4095ULL<<targetshift;
   if(regionmode&&active>0&&(seen&earlier)==earlier&&!(k.done&earlier)&&!(k.done>>targetshift&1)&&(seen&target12)==target12&&
      (m==n+1||!(seen>>(targetshift+13)&1))){
    std::array<U,12> dp,next;dp.fill(budget+1);dp[0]=0;int maximum=0;
    for(int b=0;b<active;b++){
     int owned=memory(live&(16383ULL<<(14*b)))-fixed;next.fill(budget+1);
     for(int k=0;k<=maximum;k++)if(dp[k]<=budget)for(int minimum=0;minimum<=owned&&k+minimum<12;minimum++)
      next[k+minimum]=std::min(next[k+minimum],dp[k]+std::max(blockbounds[b],regionE[minimum]));
     dp=next;maximum=std::min(11,maximum+owned);
    }
    U conditional=budget+1;
    for(int reserved=0;reserved<=maximum;reserved++)if(dp[reserved]<=budget){
     int cindex=std::max(0,3-reserved);uint32_t v;
     if(m==n+1){int row=pdbdi[(k.done>>targetshift)&16383];if(row<0)throw std::runtime_error("nonideal final-block region projection");v=regionback[cindex][row*pdbwidth+((live>>targetshift)&4095)];}
     else{int phase=int((seen>>(targetshift+12))&1);v=regionterminal[cindex][phase*terminalwidth+((live>>targetshift)&8191)];}
     if(v==UINT32_MAX)continue;
     U candidate=dp[reserved]+std::max(blockbounds[active],U(v)*(m==n+1?pdbunit:terminalunit));
     for(int b=active+1;b<4;b++)candidate+=blockbounds[b];
     conditional=std::min(conditional,candidate);
    }
    h=std::max(h,conditional);
   }
  }
  return h;
 };
 std::array<std::array<U,57>,58> hist{},exphist{};
 U initialhmin=UINT64_MAX,initialhmax=0,initialharg=0;
 std::vector<Rec> records;records.reserve(maxrecords);
 std::unordered_map<Key,Label,Hash> best;best.reserve(maxrecords);std::priority_queue<Q> queue;
 for(auto&s:seeds){Key start=normalize(make(s.live,s.done,s.m));U h=heuristic(start);if(h<initialhmin){initialhmin=h;initialharg=s.live;}initialhmax=std::max(initialhmax,h);if(memory(s.live)>cap||s.cost>budget||h>budget-s.cost)continue;auto at=best.find(start);if(at!=best.end()&&at->second.cost<=s.cost)continue;if(at==best.end())hist[progress(start)][__builtin_popcountll(start.done)]++;uint32_t id=records.size();records.push_back({start,s.cost,0,UINT32_MAX,255});best[start]={s.cost,id};queue.push({double(s.cost)+double(h)*weight,s.cost,id,s.m});}
 auto began=std::chrono::steady_clock::now();auto elapsed=[&](){return std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();};
 auto rss=[](){struct rusage r;getrusage(RUSAGE_SELF,&r);U v=r.ru_maxrss;
#ifndef __APPLE__
 v*=1024;
#endif
 return v;};
 U expanded=0,generated=0,dominated=0,pruned=0;int maxm=0,maxdone=0;std::string status="EXHAUSTED_FIXED_ORDER";uint32_t goal=UINT32_MAX;
 while(!queue.empty()){
  if(elapsed()>seconds){status="TIME_LIMIT";break;}
  if((expanded&4095)==0&&rss()>1200ULL*1024*1024){status="MEMORY_LIMIT";break;}
  Q q=queue.top();queue.pop();Rec rec=records[q.id];auto at=best.find(rec.key);if(at==best.end()||at->second.id!=q.id)continue;
  expanded++;U live=liveof(rec.key),done=rec.key.done;int m=progress(rec.key),mem=memory(live);U seen=prefix[std::min(m,n)];maxm=std::max(maxm,m);maxdone=std::max(maxdone,__builtin_popcountll(done));exphist[m][__builtin_popcountll(done)]++;
  if(m==n+1&&done==full){status="FEASIBLE";goal=q.id;break;}
  U allowed=full;
  if(demandmode){U target=0;if(m==n+1){for(int j=0;j<n;j++)if(!(done>>j&1)&&(done&ns[j].children)==ns[j].children)target|=ns[j].req;}else if(m<n)target=ns[order[m]].dep;else target=outputs;U missing=0,todo=target&~live;while(todo){int j=__builtin_ctzll(todo);U b=1ULL<<j;todo&=todo-1;if(missing&b)continue;missing|=b;todo|=ns[j].dep&~live&~missing;}allowed=missing;}
  for(int i=0;i<n;i++){
   U bit=1ULL<<i;bool old=seen&bit;
   if(live&bit||done&bit||(live&ns[i].dep)!=ns[i].dep||(!old&&(m>=n||order[m]!=i))||(old&&(!ns[i].repeat||!(allowed&bit))))continue;
   U cost=rec.cost+(old?ns[i].cost:0);if(cost>budget)continue;
   int nextm=m+int(!old);int deficit=mem+ns[i].size-cap;
   std::vector<int> choices;U possible=live&~ns[i].dep;while(possible){int j=__builtin_ctzll(possible);possible&=possible-1;choices.push_back(j);}std::sort(choices.begin(),choices.end(),[&](int a,int b){return ns[a].size>ns[b].size;});
   std::vector<int> suffix(choices.size()+1);for(int j=int(choices.size())-1;j>=0;j--)suffix[j]=suffix[j+1]+ns[choices[j]].size;
   auto emit=[&](U gone){
    generated++;Key target=normalize(make((live&~gone)|bit,done,nextm));auto found=best.find(target);if(found!=best.end()&&found->second.cost<=cost){dominated++;return;}
    U h=heuristic(target);if(h>budget-cost){pruned++;return;}
    if(records.size()>=maxrecords){status="RECORD_LIMIT";return;}
    if(found==best.end())hist[progress(target)][__builtin_popcountll(target.done)]++;
    uint32_t id=uint32_t(records.size());records.push_back({target,cost,gone,q.id,uint8_t(i)});best[target]={cost,id};int rank=std::min(progress(target),n)+2*__builtin_popcountll(target.done);queue.push({double(cost)+weight*double(h),cost,id,rank});
   };
   auto evict=[&](auto&&self,int j,int freed,int minsize,U gone)->void{
    if(status=="RECORD_LIMIT")return;
    if(freed>=deficit){if(gone==0||freed-minsize<deficit)emit(gone);return;}
    if(j==int(choices.size())||freed+suffix[j]<deficit)return;
    int node=choices[j];self(self,j+1,freed+ns[node].size,std::min(minsize,ns[node].size),gone|(1ULL<<node));self(self,j+1,freed,minsize,gone);
   };
   if(deficit<=0)emit(0);else evict(evict,0,0,1000000,0);
   if(status=="RECORD_LIMIT")break;
  }
  if(status=="RECORD_LIMIT")break;
 }
 std::cout<<"{\"status\":\""<<status<<"\",\"records\":"<<records.size()<<",\"states\":"<<best.size()<<",\"expanded\":"<<expanded<<",\"generated\":"<<generated<<",\"dominated\":"<<dominated<<",\"pruned\":"<<pruned<<",\"seconds\":"<<elapsed()<<",\"queue\":"<<queue.size()<<",\"weight\":"<<weight<<",\"max_first_progress\":"<<maxm<<",\"max_backward_done\":"<<maxdone<<",\"maxrss_bytes\":"<<rss();
 if(goal!=UINT32_MAX){
  std::vector<uint32_t> path;uint32_t root=goal;while(records[root].parent!=UINT32_MAX){path.push_back(root);root=records[root].parent;}std::reverse(path.begin(),path.end());
  std::cout<<",\"cost\":"<<records[goal].cost<<",\"initial_live\":"<<liveof(records[root].key)<<",\"initial_done\":"<<records[root].key.done<<",\"initial_progress\":"<<progress(records[root].key)<<",\"steps\":[";bool comma=false;for(auto id:path){if(comma)std::cout<<",";comma=true;std::cout<<"["<<int(records[id].node)<<","<<records[id].gone<<"]";}std::cout<<"]";
 }
 while(!queue.empty()){const Q&q=queue.top();auto at=best.find(records[q.id].key);if(at!=best.end()&&at->second.id==q.id)break;queue.pop();}
 std::cout<<",\"min_initial_h\":"<<initialhmin<<",\"max_initial_h\":"<<initialhmax<<",\"min_initial_h_live\":"<<initialharg<<",\"minimum_frontier_f\":";if(queue.empty())std::cout<<"null";else std::cout<<queue.top().f;
 U dumped=0;
 if(argc==7&&status=="EXHAUSTED_FIXED_ORDER"){
  std::ofstream out(argv[6],std::ios::binary);
  for(const auto&entry:best){U row[3]={entry.first.lp,entry.first.done,entry.second.cost};out.write(reinterpret_cast<const char*>(row),24);dumped++;}
  if(!out)throw std::runtime_error("closed label write failed");
 }
 std::cout<<",\"closed_label_rows\":"<<dumped;
 std::cout<<",\"layers\":[";bool lc=false;for(int p=0;p<58;p++)for(int d=0;d<57;d++)if(hist[p][d]||exphist[p][d]){if(lc)std::cout<<",";lc=true;std::cout<<"["<<p<<","<<d<<","<<hist[p][d]<<","<<exphist[p][d]<<"]";}std::cout<<"]}\n";return 0;
}
