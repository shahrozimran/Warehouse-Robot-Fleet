import type {Frame,Cell} from './types';
export function robotPose(frame:Frame|undefined,next:Frame|undefined,id:string,phase:number):Cell{
  const robot=frame?.robots.find(r=>r.id===id);if(!robot)return [0,0];
  const target=next?.robots.find(r=>r.id===id)?.position||robot.position;
  const t=Math.min(1,Math.max(0,phase));
  return [robot.position[0]+(target[0]-robot.position[0])*t,robot.position[1]+(target[1]-robot.position[1])*t];
}
export function worldCell(cell:Cell,width=28,height=20):[number,number,number]{return [cell[0]-(width-1)/2,0,cell[1]-(height-1)/2];}
export function statusLabel(status:string){return ({to_pick:'To pickup',to_dock:'Delivering',to_charge:'To charger',picking:'Picking',dropping:'Handoff',returning:'Returning',charging:'Charging',idle:'Available',stranded:'Stranded',queued:'Queued',assigned:'Assigned',picked:'In transit',completed:'Completed',scheduled:'Scheduled'}as Record<string,string>)[status]||status;}
