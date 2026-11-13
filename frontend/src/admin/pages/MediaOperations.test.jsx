import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import MediaOperations, { formatBytes } from './MediaOperations';
import useApi from '../../hooks/APIHandler';

jest.mock('../../hooks/APIHandler');
const mockApi = jest.fn();
const snapshot = {policy:{auto_clean_images:true,whatsapp_enabled:true,whatsapp_admin_number:'8801353529899',whatsapp_template:'store_new_order_admin',whatsapp_language:'en'},
 capacity:{database:{used_bytes:1000,budget_bytes:null,percent:null,remaining_bytes:null},object_storage:{used_bytes:null,budget_bytes:null,percent:null,remaining_bytes:null},database_image_bytes:100,image_locations:{database:1,object:0,external:0},storage_backend:'database',tracked_object_bytes:0,stale:true,recommendation:'Move media to object storage before scaling.'},
 worker:null,queue_counts:{queued:1},jobs:[{id:1,product_id:10,product_name:'Cotton shirt',slot:0,status:'queued',attempts:0,original_url:'/test-photo.png',output_url:''}],whatsapp:{configured:false,webhook_configured:false,alerts:[]},measured_at:'2026-11-13T10:00:00Z'};
beforeEach(()=>{mockApi.mockReset();useApi.mockReturnValue({callApi:mockApi});mockApi.mockResolvedValue({status:200,data:{data:snapshot}});});
test('shows unknown capacity and disconnected worker honestly',async()=>{
 render(<MediaOperations/>);
 expect(await screen.findByText('Measured storage')).toBeInTheDocument();
 expect(screen.getAllByText('Unknown headroom')).toHaveLength(2);
 expect(screen.getByText(/No recent worker heartbeat/)).toBeInTheDocument();
 expect(screen.getByText(/Meta Cloud API credentials are missing/)).toBeInTheDocument();
 expect(screen.getByRole('textbox', {name:/Admin WhatsApp number/})).toHaveValue('8801353529899');
});
test('queueing uses selected product IDs and never sends a test WhatsApp message',async()=>{
 render(<MediaOperations/>);await screen.findByText('Measured storage');
 fireEvent.change(screen.getByLabelText('Existing product IDs'),{target:{value:'10, 11'}});
 fireEvent.click(screen.getByRole('button',{name:'Queue existing photos'}));
 await waitFor(()=>expect(mockApi).toHaveBeenCalledWith(expect.objectContaining({url:'store/admin/operations/images/',method:'POST',body:{product_ids:[10,11]}})));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Queue existing photos'})).not.toBeDisabled());
 expect(mockApi.mock.calls.every(([arg])=>!arg.url.includes('whatsapp/test'))).toBe(true);
});
test('failed operations show retry instead of sample metrics',async()=>{
 mockApi.mockResolvedValue({status:503,data:{message:'Service unavailable'}});
 render(<MediaOperations/>);
 expect(await screen.findByRole('button',{name:'Retry operations'})).toBeInTheDocument();
 expect(screen.queryByText('Measured storage')).not.toBeInTheDocument();
});
test('unsaved recipient survives refresh',async()=>{
 render(<MediaOperations/>);await screen.findByText('Measured storage');
 fireEvent.change(screen.getByRole('textbox', {name:/Admin WhatsApp number/}),{target:{value:'8801700000000'}});
 fireEvent.click(screen.getByRole('button',{name:'Refresh'}));
 await waitFor(()=>expect(mockApi).toHaveBeenCalledTimes(2));
 expect(screen.getByRole('textbox', {name:/Admin WhatsApp number/})).toHaveValue('8801700000000');
});
test('byte formatting distinguishes unknown from zero',()=>{expect(formatBytes(null)).toBe('Unknown');expect(formatBytes(0)).toBe('0 B');expect(formatBytes(1024)).toBe('1.0 KiB');});
