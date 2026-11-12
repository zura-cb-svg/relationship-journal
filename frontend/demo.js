// Fictional, in-memory sample workspace. Never sends requests or persists text.
const seed = {
  user: {id:1,username:'Alex',gmail:'alex@example.com'},
  relationships: [
    {id:1,his_name:'Maya',years_together:3,problem:'Learning to make room for different rhythms, and choosing each other in the little moments.',status:'active'},
    {id:2,his_name:'Jules',years_together:6,problem:'A friendship that has changed with the seasons. Making time to reconnect.',status:'active'},
    {id:3,his_name:'Sam',years_together:2,problem:'Finding gratitude for a chapter that has ended, without needing to rewrite it.',status:'ended'},
  ],
  journal_entries: [
    {id:1,relationship_id:1,title:'The quiet Sunday',content:'We made coffee, left our phones in the other room, and watched the light move across the kitchen. Nothing extraordinary happened. Maybe that was the extraordinary part.',created_at:'2026-11-10T09:30:00Z'},
    {id:2,relationship_id:2,title:'A conversation worth keeping',content:'We talked about how much has changed since the summer. It felt good to be heard without having to explain everything.',created_at:'2026-11-08T15:00:00Z'},
    {id:3,relationship_id:1,title:'Small things, big meaning',content:'I am learning that showing up consistently matters more than grand gestures. Today I noticed three small ways we took care of each other.',created_at:'2026-11-04T12:00:00Z'},
    {id:4,relationship_id:3,title:'A softer goodbye',content:'Some chapters teach us how to start again. I want to remember the good parts without holding on to what no longer fits.',created_at:'2026-10-29T18:20:00Z'},
  ]
};
export function demoStore() {
  const data = structuredClone(seed); let rid=4, eid=5;
  const match=(s,q)=>String(s).toLowerCase().includes(q.toLowerCase());
  return {
    me:()=>structuredClone(data.user),
    dashboard:()=>({relationships:data.relationships.length,journal_entries:data.journal_entries.length,by_status:data.relationships.reduce((a,r)=>(a[r.status]=(a[r.status]||0)+1,a),Object.create(null))}),
    relationships:({search='',status='',offset=0,limit=12}={})=>data.relationships.filter(r=>(!status||r.status===status)&&(!search||match(r.his_name,search)||match(r.problem,search))).slice(offset,offset+limit).map(r=>({...r})),
    relationship:id=>({...data.relationships.find(r=>r.id===id)}),
    entries:(id,{search='',offset=0,limit=12}={})=>data.journal_entries.filter(e=>e.relationship_id===id&&(!search||match(e.title,search)||match(e.content,search))).slice(offset,offset+limit).map(e=>({...e})),
    saveRelationship:(id,body)=>{if(id){Object.assign(data.relationships.find(r=>r.id===id),body);return {...data.relationships.find(r=>r.id===id)};}const r={id:rid++,...body};data.relationships.push(r);return r;},
    saveEntry:(id,entryId,body)=>{if(entryId){const e=data.journal_entries.find(e=>e.id===entryId&&e.relationship_id===id);Object.assign(e,body);return {...e};}const e={id:eid++,relationship_id:id,...body,created_at:new Date().toISOString()};data.journal_entries.push(e);return e;},
    deleteRelationship:id=>{data.relationships=data.relationships.filter(r=>r.id!==id);data.journal_entries=data.journal_entries.filter(e=>e.relationship_id!==id);},
    deleteEntry:(id,entryId)=>{data.journal_entries=data.journal_entries.filter(e=>!(e.id===entryId&&e.relationship_id===id));},
    export:()=>structuredClone(data)
  };
}
