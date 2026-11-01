"""Offline Mem0 + learned MiniLM embeddings; SQLite authority never mounted."""
import contextlib,hashlib,io,json,logging,math,os,resource,socket,sys,time
from pathlib import Path
os.umask(0o077);sys.dont_write_bytecode=True
os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',HOME='/tmp/igris-home',MEM0_DIR='/tmp/igris-home/mem0',MEM0_TELEMETRY='false',HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
Path('/tmp/igris-home').mkdir(exist_ok=True)
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(150,150))
sys.path.insert(0,'/opt/igris/packages');logging.disable(logging.CRITICAL)
from fastembed import TextEmbedding
from mem0.embeddings.base import EmbeddingBase
from mem0.vector_stores.qdrant import Qdrant
from mem0.utils.factory import LlmFactory,EmbedderFactory,VectorStoreFactory
from mem0 import Memory

class NoExtraction:
    calls=0
    def __init__(self,config):self.config=config
    def generate_response(self,*args,**kwargs):
        type(self).calls+=1;raise PermissionError('Mem0 extraction disabled; Hermes is the only reasoning runtime.')

class OfflineEmbedding(EmbeddingBase):
    calls=0
    def __init__(self,config):
        super().__init__(config)
        if config.model!='sentence-transformers/all-MiniLM-L6-v2' or config.embedding_dims!=384:raise ValueError('Only pinned local MiniLM permitted.')
        self.model=TextEmbedding(model_name=config.model,specific_model_path='/models/minilm',cache_dir='/tmp/fastembed',local_files_only=True,threads=1,providers=['CPUExecutionProvider'])
        self.model.model.tokenizer.no_truncation()
    def embed(self,text,memory_action=None):
        if not isinstance(text,str) or self.model.token_count(text)>256:raise ValueError('Explicit embedding token limit; no silent truncation.')
        type(self).calls+=1;vector=list(self.model.embed(text,batch_size=1,parallel=None))[0].tolist()
        if len(vector)!=384 or not all(math.isfinite(x) for x in vector):raise ValueError('Invalid actual embedding.')
        return vector

class DenseQdrant(Qdrant):
    # This adapter intentionally excludes optional sparse-model downloads/ranking.
    def _get_bm25_encoder(self):return None
    def keyword_search(self,*args,**kwargs):return None


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate input field.')
        result[key]=value
    return result


def main():
    import re
    started=time.monotonic();packet=json.loads(sys.stdin.buffer.read(32769),object_pairs_hook=unique)
    if type(packet) is not dict or set(packet)!={'scope','snapshot_sha256','query','probe_extraction_denial'} or any(not re.fullmatch('[a-f0-9]{64}',packet[key]) for key in ('scope','snapshot_sha256')) or type(packet['query']) is not str or len(packet['query'])>512 or type(packet['probe_extraction_denial']) is not bool:raise ValueError('Invalid fixed memory packet.')
    raw=Path('/input/facts.json').read_bytes()
    if len(raw)>8*1024**2 or hashlib.sha256(raw).hexdigest()!=packet['snapshot_sha256']:raise ValueError('Approved snapshot hash/size mismatch.')
    snapshot=json.loads(raw,object_pairs_hook=unique)
    if type(snapshot) is not dict or set(snapshot)!={'scope','facts'} or snapshot['scope']!=packet['scope'] or type(snapshot['facts']) is not list or len(snapshot['facts'])>1000:raise ValueError('Invalid scope snapshot.')
    facts={}
    for item in snapshot['facts']:
        if type(item) is not dict or set(item)!={'id','revision','text'} or not re.fullmatch('[a-f0-9]{32}',item['id']) or type(item['revision']) is not int or item['revision']<1 or type(item['text']) is not str or not item['text'] or len(item['text'])>512 or item['id'] in facts:raise ValueError('Invalid approved fact.')
        facts[item['id']]=item
    if os.getuid()==0 or Path('/var/run/docker.sock').exists():raise ValueError('Unprivileged isolated memory worker required.')
    try:socket.create_connection(('192.0.2.1',9),timeout=.2)
    except OSError as exc:
        if exc.errno!=101:raise
    else:raise ValueError('External network must be absent.')
    for provider in LlmFactory.get_supported_providers():LlmFactory.register_provider(provider,'__main__.NoExtraction')
    EmbedderFactory.provider_to_class={'fastembed':'__main__.OfflineEmbedding'}
    VectorStoreFactory.provider_to_class={'qdrant':'__main__.DenseQdrant'}
    config={'llm':{'provider':'lmstudio','config':{'model':'extraction-disabled','enable_vision':False}},'embedder':{'provider':'fastembed','config':{'model':'sentence-transformers/all-MiniLM-L6-v2','embedding_dims':384}},
            'vector_store':{'provider':'qdrant','config':{'collection_name':'igris_facts','embedding_model_dims':384,'path':'/state/qdrant','on_disk':True}},'history_db_path':'/state/history.sqlite3'}
    with contextlib.redirect_stdout(io.StringIO()):
        memory=Memory.from_config(config)
        from mem0.memory import telemetry
        if telemetry.MEM0_TELEMETRY or type(memory.llm) is not NoExtraction:raise ValueError('Extraction/telemetry policy mismatch.')
        manifest_path=Path('/state/manifest.json');manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'scope':packet['scope'],'entries':{}}
        if manifest.get('scope')!=packet['scope']:raise ValueError('Index scope mismatch.')
        mapping=manifest['entries']
        try:
            for ident,previous in list(mapping.items()):
                if ident not in facts or (previous['revision']!=facts[ident]['revision'] or previous.get('text_sha256')!=hashlib.sha256(facts[ident]['text'].encode()).hexdigest()):memory.delete(previous['mem0_id']);mapping.pop(ident)
            for ident,item in facts.items():
                if ident in mapping:continue
                added=memory.add(item['text'],user_id=packet['scope'],metadata={'igris_id':ident,'igris_revision':item['revision']},infer=False)
                result=added['results']
                if len(result)!=1 or result[0]['event']!='ADD':raise ValueError('Actual Mem0 insertion not verified.')
                mapping[ident]={'revision':item['revision'],'mem0_id':result[0]['id'],'text_sha256':hashlib.sha256(item['text'].encode()).hexdigest()}
            temporary=manifest_path.with_suffix('.next');temporary.write_text(json.dumps(manifest,sort_keys=True));temporary.replace(manifest_path)
            denied=False
            if packet['probe_extraction_denial']:
                try:memory.llm.generate_response(messages=[{'role':'user','content':'Security probe: extraction must remain disabled.'}])
                except PermissionError:denied=True
                else:raise ValueError('Extraction unexpectedly enabled.')
            results=[]
            if packet['query']:
                found=memory.search(packet['query'],filters={'user_id':packet['scope']},top_k=8,threshold=0.0)
                for item in found['results']:
                    meta=item.get('metadata') or {}
                    results.append({'id':meta.get('igris_id'),'revision':meta.get('igris_revision'),'score':item['score']})
            if NoExtraction.calls!=int(denied):raise ValueError('Unexpected extraction invocation.')
        finally:memory.vector_store.client.close()
    output={'origin':'real_mem0_local','scope':packet['scope'],'snapshot_sha256':packet['snapshot_sha256'],'results':results,'indexed_facts':len(mapping),'embedding_calls':OfflineEmbedding.calls,
            'extraction_calls':NoExtraction.calls,'extraction_probe_denied':denied,'telemetry_enabled':False,'elapsed_seconds':time.monotonic()-started,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    print(json.dumps(output,allow_nan=False),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:print(json.dumps({'status':'failed','error_type':type(exc).__name__}),flush=True);raise SystemExit(1)
