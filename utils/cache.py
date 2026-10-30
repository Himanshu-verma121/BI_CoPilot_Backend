import redis          
import json           
import hashlib        
from config import settings

try:
    redis_client = redis.Redis(
        host             = settings.REDIS_HOST,
        port             = settings.REDIS_PORT,
        decode_responses = True   
    )
    # Test connection
    redis_client.ping()
    print("Redis connected successfully")

except Exception as e:
    redis_client = None
    print(f"Redis not available: {e} — continuing without cache")


def generate_cache_key(company_id: int, connection_id: int, question: str) -> str:
    normalized = f"{company_id}_{connection_id}_{question.lower().strip()}"

    cache_key = hashlib.md5(normalized.encode()).hexdigest()

    return f"bi_query:{cache_key}"


def get_cached_result(company_id: int, connection_id: int, question: str):
    if not redis_client:
        return None

    try:
        key    = generate_cache_key(company_id, connection_id, question)
        cached = redis_client.get(key)

        if cached:
            # Found in cache!
            result              = json.loads(cached)
            result["was_cached"] = True   
            print(f"Cache HIT for key: {key[:20]}...")
            return result

        print(f"Cache MISS for key: {key[:20]}...")
        return None

    except Exception as e:
        print(f"Cache read error: {e}")
        return None


def set_cached_result(
    company_id    : int,
    connection_id : int,
    question      : str,
    result        : dict,
    ttl_seconds   : int = 3600    
):
    if not redis_client:
        return

    try:
        key = generate_cache_key(company_id, connection_id, question)

        cache_result = {k: v for k, v in result.items() if k != "chart"}

        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(cache_result)
        )
        print(f"Cached result for {ttl_seconds}s: {key[:20]}...")

    except Exception as e:
        print(f"Cache write error: {e}")


def delete_cached_results(company_id: int, connection_id: int):
    if not redis_client:
        return

    try:
        pattern = f"bi_query:*"
        keys    = redis_client.keys(pattern)

        if keys:
            redis_client.delete(*keys)
            print(f"Deleted {len(keys)} cached results")

    except Exception as e:
        print(f"Cache delete error: {e}")


def get_cache_stats():
    if not redis_client:
        return {"available": False}

    try:
        info       = redis_client.info()
        all_keys   = redis_client.keys("bi_query:*")

        return {
            "available"     : True,
            "total_keys"    : len(all_keys),
            "memory_used"   : info.get("used_memory_human", "N/A"),
            "hits"          : info.get("keyspace_hits", 0),
            "misses"        : info.get("keyspace_misses", 0),
            "hit_rate"      : round(
                info.get("keyspace_hits", 0) /
                max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
                * 100, 2
            )
        }
    except Exception as e:
        return {"available": False, "error": str(e)}