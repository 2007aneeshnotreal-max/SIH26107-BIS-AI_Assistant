export type Language='en'|'hi'
export interface Citation {id:number;ordinal:number;label:string;source_title:string;document_id:string;standard_number:string;section:string;page:number|null;source_url:string;source_type:string;excerpt:string}
export interface LabResult {name:string;location:string;valid_until:string;status:string;scope_status:string;url:string}
export interface Message {id:number;role:'user'|'assistant';content:string;intent:string;confidence:number|null;abstained:boolean;citations:Citation[];next_steps:string[];lab_results?:LabResult[];created_at:string}
export interface Session {public_id:string;title:string;audience:string;language:Language;is_pinned:boolean;messages:Message[]}
export interface Standard {id:number;number:string;title:string;aspect:string;department:string;committee:string;scope:string;is_demo:boolean;confidence?:string;reason?:string;disclaimer?:string}
export interface GuideStep {order:number;title:string;description:string;checklist:string[];links:{label:string;url:string}[];estimated_next_step:string}
export interface Guide {slug:string;title:string;summary:string;scheme:string;is_demo:boolean;steps:GuideStep[]}
