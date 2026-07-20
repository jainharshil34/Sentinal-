import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.data.incidents import INCIDENT_CORPUS

# Global models cached in-memory
_model = None
_embeddings = None
_cached_corpus = None

def get_model():
    global _model
    if _model is None:
        # Load local lightweight sentence transformer model
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        import socket
        orig_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(15.0)
            _cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        finally:
            socket.setdefaulttimeout(orig_timeout)
    return _cross_encoder

def reset_incident_cache():
    """
    Clears the in-memory cache to force reloading from the database.
    """
    global _embeddings, _cached_corpus
    _embeddings = None
    _cached_corpus = None

def get_active_corpus(db=None) -> list[dict]:
    """
    Retrieves the corpus from the persistent database incident_history table.
    Falls back to static INCIDENT_CORPUS if the database is empty or unavailable.
    """
    close_db = False
    if db is None:
        from app.db.database import SessionLocal
        db = SessionLocal()
        close_db = True
        
    try:
        from app.db import models
        records = db.query(models.IncidentHistory).all()
        if not records:
            return INCIDENT_CORPUS
            
        corpus = []
        for r in records:
            corpus.append({
                "id": r.id,
                "text": r.contributing_factors,
                "rule_type": r.related_rule_type or "UNSUPPORTED_RULE",
                "regulatory_clause": r.regulatory_clause or "",
                "zone": r.zone,
                "plant_id": r.plant_id,
                "time_offset_desc": "recently",
                "source": r.source or "synthetic"
            })
        return corpus
    except Exception as e:
        print(f"Error reading corpus from database, using static fallback: {e}")
        return INCIDENT_CORPUS
    finally:
        if close_db:
            db.close()

def refresh_embeddings(db=None):
    """
    Forces embedding calculation on the current database corpus and updates the global cache.
    """
    global _embeddings, _cached_corpus
    model = get_model()
    corpus = get_active_corpus(db)
    texts = [r["text"] for r in corpus]
    if texts:
        _embeddings = model.encode(texts, convert_to_numpy=True)
    else:
        _embeddings = np.array([])
    _cached_corpus = corpus

def get_embeddings(db=None):
    global _embeddings
    if _embeddings is None:
        refresh_embeddings(db)
    return _embeddings

def get_cached_corpus(db=None):
    global _cached_corpus
    if _cached_corpus is None:
        _cached_corpus = get_active_corpus(db)
    return _cached_corpus

def cosine_similarity(a, b):
    # a: 1D query embedding, b: 2D corpus embeddings
    if b.size == 0:
        return np.array([])
    dot = np.dot(b, a)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b, axis=1)
    norm_b = np.where(norm_b == 0, 1e-9, norm_b)
    return dot / (norm_a * norm_b)

def query_intelligence(query_text: str, top_k: int = 5) -> list[dict]:
    """
    Incident Pattern Intelligence query engine.
    Combines:
      - Layer A: Semantic similarity search (local sentence embedding)
      - Layer B: Multi-Hop knowledge graph traversal (connecting shared rules/clauses)
    """
    from app.db.database import SessionLocal
    with SessionLocal() as db:
        model = get_model()
        corpus_embs = get_embeddings(db)
        corpus = get_cached_corpus(db)
        
        if corpus_embs.size == 0 or len(corpus) == 0:
            return []
            
        # 1. Embed query
        query_emb = model.encode(query_text, convert_to_numpy=True)
        
        # 2. Compute similarity
        sims = cosine_similarity(query_emb, corpus_embs)
        if sims.size == 0:
            return []
            
        # Build list of semantic matches
        semantic_matches = []
        for idx, sim in enumerate(sims):
            if idx < len(corpus):
                report = corpus[idx].copy()
                report["score"] = float(sim)
                semantic_matches.append(report)
            
        # Sort semantic matches descending
        semantic_matches.sort(key=lambda x: x["score"], reverse=True)
        
        # Take the top 3 as the primary seeds for knowledge graph traversal
        top_3_seeds = semantic_matches[:3]
        
        results_map = {}
        
        # Initialize results map with seeds
        for rank, r in enumerate(top_3_seeds):
            r_id = r["id"]
            results_map[r_id] = {
                "id": r_id,
                "text": r["text"],
                "rule_type": r["rule_type"],
                "regulatory_clause": r["regulatory_clause"],
                "zone": r["zone"],
                "plant_id": r.get("plant_id"),
                "time_offset_desc": r.get("time_offset_desc"),
                "fleet_summary": f"A similar compound-risk pattern occurred at {r.get('plant_id')} {r.get('time_offset_desc', 'recently')}.",
                "score": r["score"],
                "reasons": ["Semantic match"],
                "seed_rank": rank,
                "source": r.get("source", "synthetic")
            }
            
        # 3. Knowledge Graph Traversal (Multi-Hop Cross-Linking)
        # Traverse from top N semantic matches to related incidents sharing the same rule or clause
        for rank, seed in enumerate(top_3_seeds):
            seed_rule = seed.get("rule_type")
            seed_clause = seed.get("regulatory_clause")
            
            for candidate in corpus:
                cand_id = candidate["id"]
                if cand_id == seed["id"]:
                    continue
                    
                reasons = []
                if seed_rule and seed_rule == candidate.get("rule_type") and seed_rule not in ["UNSUPPORTED_RULE", "CLERICAL_ERROR", "COMPLIANCE_AUDIT", "ROUTINE_CALIBRATION", "ROUTINE_SAFETY"]:
                    reasons.append(f"Shared rule type: {seed_rule}")
                if seed_clause and seed_clause == candidate.get("regulatory_clause"):
                    reasons.append(f"Shared regulatory clause: {seed_clause}")
                    
                if reasons:
                    # Calculate candidate's native semantic similarity score
                    try:
                        cand_idx = next(i for i, c in enumerate(corpus) if c["id"] == cand_id)
                        cand_sim = float(sims[cand_idx])
                    except Exception:
                        cand_sim = 0.0
                        
                    if cand_id in results_map:
                        # Append new traversal explanations to existing match
                        for r in reasons:
                            if r not in results_map[cand_id]["reasons"]:
                                results_map[cand_id]["reasons"].append(r)
                        if results_map[cand_id]["seed_rank"] >= 10:
                            results_map[cand_id]["seed_rank"] = min(results_map[cand_id]["seed_rank"], 10 + rank)
                    else:
                        results_map[cand_id] = {
                            "id": cand_id,
                            "text": candidate["text"],
                            "rule_type": candidate["rule_type"],
                            "regulatory_clause": candidate["regulatory_clause"],
                            "zone": candidate["zone"],
                            "plant_id": candidate.get("plant_id"),
                            "time_offset_desc": candidate.get("time_offset_desc"),
                            "fleet_summary": f"A similar compound-risk pattern occurred at {candidate.get('plant_id')} {candidate.get('time_offset_desc', 'recently')}.",
                            "score": cand_sim,
                            "reasons": reasons,
                            "seed_rank": 10 + rank,
                            "source": candidate.get("source", "synthetic")
                        }
    
        # 4. Final Sorting and Top-K Selection
        sorted_results = list(results_map.values())
        sorted_results.sort(key=lambda x: (x["seed_rank"], -x["score"]))
        
        # Cross-encoder re-ranking on top 8 candidates
        candidates = sorted_results[:8]
        other_results = sorted_results[8:]
        
        if candidates:
            try:
                cross_encoder = get_cross_encoder()
                pairs = [(query_text, c["text"]) for c in candidates]
                raw_scores = cross_encoder.predict(pairs)
                
                if isinstance(raw_scores, float):
                    raw_scores = [raw_scores]
                    
                for idx, c in enumerate(candidates):
                    raw_score = float(raw_scores[idx])
                    ce_score = 1.0 / (1.0 + np.exp(-raw_score))
                    
                    if len(candidates) > 1:
                        norm_graph = 1.0 - (idx / (len(candidates) - 1))
                    else:
                        norm_graph = 1.0
                        
                    c["score"] = 0.6 * ce_score + 0.4 * norm_graph
                    
                # Re-sort candidates descending by their new blended score
                candidates.sort(key=lambda x: x["score"], reverse=True)
            except Exception as e:
                print(f"Cross-encoder re-ranking failed in query_intelligence: {e}")
                
        re_ranked_results = candidates + other_results
        return re_ranked_results[:top_k]

def detect_recurring_patterns() -> list[dict]:
    """
    Layer C: Cross-corpus recurring pattern clustering and ranking.
    Identifies which regulatory clauses and rule types occur most frequently across the corpus.
    """
    from app.db.database import SessionLocal
    with SessionLocal() as db:
        corpus = get_cached_corpus(db)
        
        rule_counts = {}
        clause_counts = {}
        for r in corpus:
            rule = r.get("rule_type")
            clause = r.get("regulatory_clause")
            if rule and rule not in ["UNSUPPORTED_RULE", "CLERICAL_ERROR", "COMPLIANCE_AUDIT", "ROUTINE_CALIBRATION", "ROUTINE_SAFETY"]:
                rule_counts[rule] = rule_counts.get(rule, 0) + 1
            if clause:
                clause_counts[clause] = clause_counts.get(clause, 0) + 1
                
        patterns = []
        total_incidents = len(corpus)
        if total_incidents == 0:
            return []
            
        # Append Clause-based patterns
        for clause, count in clause_counts.items():
            desc = f"Pattern: {count} of {total_incidents} incidents in this corpus trace back to regulatory clause {clause} — this is your top systemic risk category, not an isolated event."
            patterns.append({
                "category": f"Clause: {clause}",
                "count": count,
                "percentage": round((count / total_incidents) * 100, 1),
                "description": desc,
                "type": "clause",
                "key": clause
            })
            
        # Append Rule-based patterns
        for rule, count in rule_counts.items():
            desc = f"Pattern: {count} of {total_incidents} incidents in this corpus trace back to rule {rule}."
            patterns.append({
                "category": f"Rule: {rule}",
                "count": count,
                "percentage": round((count / total_incidents) * 100, 1),
                "description": desc,
                "type": "rule",
                "key": rule
            })
            
        # Sort by count descending
        patterns.sort(key=lambda x: x["count"], reverse=True)
        return patterns

def get_related_incidents_for_rules(triggered_rules: list[dict], top_k: int = 4) -> list[dict]:
    """
    Auto-trigger helper: takes active live triggered rules, executes graph-traversal
    and semantic query, and returns related historical incidents.
    """
    if not triggered_rules:
        return []
        
    from app.db.database import SessionLocal
    with SessionLocal() as db:
        corpus = get_cached_corpus(db)
        corpus_embs = get_embeddings(db)
        
        results_map = {}
        sims = None
        
        # We can perform traversal using the triggered rules as seed nodes
        for rule in triggered_rules:
            rule_name = rule.get("rule_name")
            reason = rule.get("reason", "")
            
            # Traverse via Rule Type matching
            for candidate in corpus:
                cand_id = candidate["id"]
                reasons = []
                
                if rule_name and rule_name == candidate.get("rule_type"):
                    reasons.append(f"Shared rule type: {rule_name}")
                    
                # If the rule description mentions standard clauses (e.g. OISD 105, OSHA 1910.146, IE Rule 1956)
                cand_clause = candidate.get("regulatory_clause")
                if cand_clause and cand_clause.lower() in reason.lower():
                    reasons.append(f"Shared regulatory clause: {cand_clause}")
                    
                if reasons:
                    if cand_id in results_map:
                        for r in reasons:
                            if r not in results_map[cand_id]["reasons"]:
                                results_map[cand_id]["reasons"].append(r)
                    else:
                        results_map[cand_id] = {
                            "id": cand_id,
                            "text": candidate["text"],
                            "rule_type": candidate["rule_type"],
                            "regulatory_clause": candidate["regulatory_clause"],
                            "zone": candidate["zone"],
                            "reasons": reasons,
                            "score": 0.0
                        }
                        
            # Also run a quick semantic query using the rule's explanation text
            try:
                model = get_model()
                query_emb = model.encode(reason, convert_to_numpy=True)
                sims = cosine_similarity(query_emb, corpus_embs)
                
                for idx, sim in enumerate(sims):
                    if idx < len(corpus):
                        cand_id = corpus[idx]["id"]
                        if sim > 0.35: # Semantic correlation threshold
                            reason_str = "Semantic match"
                            if cand_id in results_map:
                                results_map[cand_id]["score"] = max(results_map[cand_id]["score"], float(sim))
                                if reason_str not in results_map[cand_id]["reasons"]:
                                    results_map[cand_id]["reasons"].append(reason_str)
                            else:
                                candidate = corpus[idx]
                                results_map[cand_id] = {
                                    "id": cand_id,
                                    "text": candidate["text"],
                                    "rule_type": candidate["rule_type"],
                                    "regulatory_clause": candidate["regulatory_clause"],
                                    "zone": candidate["zone"],
                                    "reasons": [reason_str],
                                    "score": float(sim)
                                }
            except Exception as e:
                print("Auto-trigger semantic embedding failed, relying on graph-only matches", e)
    
        sorted_results = list(results_map.values())
        # Sort by reasons count, then semantic score
        sorted_results.sort(key=lambda x: (len(x["reasons"]), x["score"]), reverse=True)
        
        # Cross-encoder re-ranking on top 8 candidates
        candidates = sorted_results[:8]
        other_results = sorted_results[8:]
        
        if candidates:
            try:
                cross_encoder = get_cross_encoder()
                query_text = " ".join([r.get("reason", "") for r in triggered_rules if r.get("reason")])
                if not query_text:
                    query_text = " ".join([r.get("rule_name", "") for r in triggered_rules if r.get("rule_name")])
                    
                pairs = [(query_text, c["text"]) for c in candidates]
                raw_scores = cross_encoder.predict(pairs)
                
                if isinstance(raw_scores, float):
                    raw_scores = [raw_scores]
                    
                for idx, c in enumerate(candidates):
                    raw_score = float(raw_scores[idx])
                    ce_score = 1.0 / (1.0 + np.exp(-raw_score))
                    
                    if len(candidates) > 1:
                        norm_graph = 1.0 - (idx / (len(candidates) - 1))
                    else:
                        norm_graph = 1.0
                        
                    c["score"] = 0.6 * ce_score + 0.4 * norm_graph
                    
                # Re-sort candidates descending by their new blended score
                candidates.sort(key=lambda x: x["score"], reverse=True)
            except Exception as e:
                print(f"Cross-encoder re-ranking failed in get_related_incidents_for_rules: {e}")
                
        re_ranked_results = candidates + other_results
        return re_ranked_results[:top_k]

def generate_fallback_briefing(query_text: str, results: list[dict]) -> str:
    """
    Deterministic safety briefing generator if Claude/Gemini APIs are unavailable.
    """
    if not results:
        return "No historical incidents retrieved. SentinelGrid cannot synthesize a systemic risk pattern."
        
    rule_types = list(set(r.get("rule_type") for r in results if r.get("rule_type")))
    clauses = list(set(r.get("regulatory_clause") for r in results if r.get("regulatory_clause")))
    
    real_count = sum(1 for r in results if r.get("source") == "real_incident")
    synthetic_count = len(results) - real_count
    
    source_summary = ""
    if real_count > 0 and synthetic_count > 0:
        source_summary = f"{real_count} real-world (CSB/OSHA) record(s) and {synthetic_count} synthetic scenario(s)"
    elif real_count > 0:
        source_summary = f"{real_count} real-world (CSB/OSHA) record(s)"
    else:
        source_summary = f"{synthetic_count} synthetic scenario(s)"
        
    recommendation = "Establish robust isolation procedures and verify monitoring equipment calibration."
    if clauses:
        clause_list = ", ".join(clauses)
        if any("105" in c for c in clauses):
            recommendation = "Enforce hot work permits, clear combustible gas presence, and establish strict fire watches."
        elif any("112" in c or "36" in c for c in clauses):
            recommendation = "Ensure mandatory atmospheric testing before confined space entries and active ventilation."
        elif any("37" in c or "137" in c for c in clauses):
            recommendation = "Conduct periodic electrical checks and enforce lock-out-tag-out (LOTO) protocols."
        clause_citation = f" under compliance guidelines ({clause_list})"
    else:
        clause_citation = ""
        
    briefing = (
        f"SentinelGrid Analysis: The search for '{query_text}' linked {len(results)} records ({source_summary}). "
        f"A shared pattern involves safety concerns in category {', '.join(rule_types[:2])}. "
        f"To prevent recurrence{clause_citation}, we recommend you: {recommendation}"
    )
    return briefing

def generate_pattern_briefing(query_text: str, results: list[dict], db=None) -> str:
    """
    Generates an AI-synthesized systemic risk briefing using Claude (or Gemini fallback) 
    based on the query text and retrieved historical incidents.
    """
    import os
    import json
    import requests
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not gemini_key and not anthropic_key:
        return generate_fallback_briefing(query_text, results)
        
    system_prompt = (
        "You are an industrial safety expert. You will synthesize a short 'systemic risk briefing' paragraph "
        "based on a query and a set of retrieved historical incidents.\n"
        "Strict constraints:\n"
        "1. Identify the common root-cause pattern across the retrieved incidents.\n"
        "2. Cite which incidents are real (CSB/OSHA) vs synthetic.\n"
        "3. Provide one specific preventive recommendation tied to their shared regulatory clause.\n"
        "4. The entire briefing must be a single cohesive paragraph and must be strictly under 120 words."
    )
    
    incidents_str = ""
    for idx, r in enumerate(results):
        incidents_str += (
            f"Incident {idx+1}:\n"
            f"  Rule Type: {r.get('rule_type')}\n"
            f"  Regulatory Clause: {r.get('regulatory_clause')}\n"
            f"  Description: {r.get('text')}\n"
            f"  Source: {'real (CSB/OSHA)' if r.get('source') == 'real_incident' else 'synthetic'}\n\n"
        )
        
    user_content = f"Query: {query_text}\n\nRetrieved Incidents:\n{incidents_str}"
    
    # 1. Try Gemini
    if gemini_key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": user_content
                        }
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {
                        "text": system_prompt
                    }
                ]
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text
            else:
                print(f"Gemini API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            
    # 2. Try Anthropic
    if anthropic_key:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_content}
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                res_json = response.json()
                text = res_json["content"][0]["text"].strip()
                return text
            else:
                print(f"Anthropic API returned status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            
    return generate_fallback_briefing(query_text, results)
