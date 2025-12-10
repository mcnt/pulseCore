import hashlib
import math
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple



# CONSTANTES DO SISTEMA
POSITIVE_WORDS = {
    "adorei", "gostei", "bom", "otimo", "ótimo",
    "excelente", "perfeito", "produto",
    "servico", "serviço", "ótima", "otima",
}

NEGATIVE_WORDS = {
    "ruim", "terrivel", "terrível", "péssimo", "pessimo",
    "horrivel", "horrível", "péssima", "pessima",
}

INTENSIFIERS = {"muito", "super"}
NEGATIONS = {"nao", "não"}
SPECIAL_META_TRIGGER = "teste tecnico mbras"



# FUNÇÕES UTILITÁRIAS
def normalize_text(text: str) -> str:
    """Remove acentuação e converte para lowercase ASCII."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def tokenize(text: str) -> List[str]:
    """Tokenização simples preservando hashtags e underscores."""
    tokens = []
    current_token_chars = []

    for character in text:
        if character.isalnum() or character in {"#", "_"}:
            current_token_chars.append(character)
        else:
            if current_token_chars:
                tokens.append("".join(current_token_chars))
                current_token_chars = []
    if current_token_chars:
        tokens.append("".join(current_token_chars))

    return tokens



# ANÁLISE DE SENTIMENTO POR MENSAGEM
def compute_sentiment_for_message(content: str, user_id: str) -> Tuple[float, str]:
    tokens = tokenize(content)
    if not tokens:
        return 0.0, "neutral"

    normalized_tokens = [normalize_text(token) for token in tokens]
    normalized_content = normalize_text(content)
    
    if normalized_content == normalize_text(SPECIAL_META_TRIGGER):
        return 0.0, "meta"

    sentiment_hits: List[Tuple[int, float]] = []

    for index, token in enumerate(normalized_tokens):
        if token in POSITIVE_WORDS:
            sentiment_hits.append((index, 1.0))
        elif token in NEGATIVE_WORDS:
            sentiment_hits.append((index, -1.0))

    # Caso de frases apenas com intensificadores
    if not sentiment_hits and all(token in INTENSIFIERS for token in normalized_tokens):
        return 0.0, "neutral"

    if not sentiment_hits:
        return 0.0, "neutral"

    sentiment_score_sum = 0.0

    for index, base_value in sentiment_hits:
        sentiment_value = base_value

        # Intensificadores antes da palavra
        if index - 1 >= 0 and normalized_tokens[index - 1] in INTENSIFIERS:
            sentiment_value *= 1.5

        # Negação nos 3 tokens anteriores
        negation_count = sum(
            1 for j in range(max(0, index - 3), index)
            if normalized_tokens[j] in NEGATIONS
        )
        if negation_count % 2 == 1:
            sentiment_value *= -1

        if "mbras" in normalize_text(user_id) and sentiment_value > 0:
            sentiment_value *= 2.0

        sentiment_score_sum += sentiment_value

    final_score = sentiment_score_sum / len(sentiment_hits)

    if final_score > 0.1:
        label = "positive"
    elif final_score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return final_score, label



# INFLUÊNCIA / FOLLOWERS FAKE
def get_follower_count(user_id: str) -> int:
    """Simula contagem de seguidores baseada em padrões do user_id."""
    if user_id == "user_café":
        return 4242

    if len(user_id) == 13:
        return 233

    if user_id.endswith("_prime"):
        base_value = (int(hashlib.sha256(user_id.encode("utf-8")).hexdigest(), 16) % 1000) + 100

        def is_prime(n: int) -> bool:
            if n < 2:
                return False
            if n % 2 == 0:
                return n == 2
            limit = int(math.sqrt(n))
            divisor = 3
            while divisor <= limit:
                if n % divisor == 0:
                    return False
                divisor += 2
            return True

        next_prime = base_value
        while not is_prime(next_prime):
            next_prime += 1
        return next_prime

    return (int(hashlib.sha256(user_id.encode("utf-8")).hexdigest(), 16) % 10000) + 100



# ENGAGEMENT RATE
def compute_engagement_rate(reactions: int, shares: int, views: int) -> float:
    if views <= 0:
        return 0.0

    base_rate = (reactions + shares) / float(views)
    total_interactions = reactions + shares

    # Bônus se divisível por 7
    if total_interactions > 0 and total_interactions % 7 == 0:
        golden_ratio = (1 + 5 ** 0.5) / 2
        base_rate *= 1 + 1 / golden_ratio

    return base_rate



# DISTRIBUIÇÃO DE SENTIMENTO
def compute_sentiment_distribution(scores_and_labels: List[Tuple[float, str]]) -> Dict[str, float]:
    label_count = Counter()
    total = 0

    for _, label in scores_and_labels:
        if label != "meta":
            label_count[label] += 1
            total += 1

    if total == 0:
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

    return {
        "positive": label_count["positive"] * 100.0 / total,
        "negative": label_count["negative"] * 100.0 / total,
        "neutral": label_count["neutral"] * 100.0 / total,
    }



# FLAGS ESPECIAIS
def compute_flags(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined_content = " ".join(message["content"] for message in messages)
    combined_user_ids = " ".join(message["user_id"] for message in messages)

    normalized_content = normalize_text(combined_content)
    normalized_user_ids = normalize_text(combined_user_ids)

    flags = {
        "mbras_employee": "mbras" in normalized_user_ids,
        "candidate_awareness": SPECIAL_META_TRIGGER in normalized_content,
        "special_pattern": any(
            len(message["content"]) == 42 and "mbras" in normalize_text(message["content"])
            for message in messages
        ),
    }
    return flags



# TRENDING TOPICS
def compute_trending_topics(messages: List[Dict[str, Any]], now_reference: datetime, message_labels: Dict[str, str]) -> List[str]:
    hashtag_weights: Dict[str, float] = defaultdict(float)
    hashtag_frequency: Dict[str, int] = defaultdict(int)

    for message in messages:
        timestamp: datetime = message["timestamp"]
        minutes_since = max((now_reference - timestamp).total_seconds() / 60.0, 1.0)

        time_weight = 1.0 + (1.0 / minutes_since)

        sentiment_label = message_labels.get(message["id"], "neutral")
        sentiment_multiplier = 1.2 if sentiment_label == "positive" else 0.8 if sentiment_label == "negative" else 1.0

        for hashtag in message.get("hashtags", []):
            base_weight = 1.0
            if len(hashtag) > 8:
                base_weight *= math.log10(len(hashtag)) / math.log10(8)

            final_weight = base_weight * time_weight * sentiment_multiplier

            hashtag_weights[hashtag] += final_weight
            hashtag_frequency[hashtag] += 1

    if not hashtag_weights:
        return []

    sorted_hashtags = sorted(
        hashtag_weights.keys(),
        key=lambda h: (-hashtag_weights[h], -hashtag_frequency[h], h),
    )

    return sorted_hashtags[:5]



# ANOMALY DETECTION (placeholder)
def detect_anomaly(messages: List[Dict[str, Any]]) -> bool:
    return False



# FUNÇÃO PRINCIPAL
def analyze_feed(messages: List[Dict[str, Any]], time_window_minutes: int) -> Dict[str, Any]:
    if not messages:
        return {
            "sentiment_distribution": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
            "engagement_score": 0.0,
            "trending_topics": [],
            "influence_ranking": [],
            "anomaly_detected": False,
            "flags": {"mbras_employee": False, "candidate_awareness": False, "special_pattern": False},
            "processing_time_ms": 0.0,
        }

    # Normaliza timestamps
    parsed_messages: List[Dict[str, Any]] = []
    latest_timestamp = None

    for message in messages:
        raw_timestamp = message["timestamp"]
        if isinstance(raw_timestamp, str):
            timestamp_dt = datetime.strptime(raw_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        else:
            timestamp_dt = raw_timestamp

        message_copy = dict(message)
        message_copy["timestamp"] = timestamp_dt
        parsed_messages.append(message_copy)

        if latest_timestamp is None or timestamp_dt > latest_timestamp:
            latest_timestamp = timestamp_dt

    now_reference = latest_timestamp or datetime.now(timezone.utc)
    time_window_delta = timedelta(minutes=time_window_minutes)

    lower_bound = now_reference - time_window_delta
    window_messages = [msg for msg in parsed_messages if lower_bound <= msg["timestamp"] <= now_reference + timedelta(seconds=5)]


    if not window_messages:
        return {
            "sentiment_distribution": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
            "engagement_score": 0.0,
            "trending_topics": [],
            "influence_ranking": [],
            "anomaly_detected": False,
            "flags": {"mbras_employee": False, "candidate_awareness": False, "special_pattern": False},
            "processing_time_ms": 0.0,
        }

    per_message_scores: List[Tuple[float, str]] = []
    message_labels: Dict[str, str] = {}

    for message in window_messages:
        sentiment_score, sentiment_label = compute_sentiment_for_message(message["content"], message["user_id"])
        per_message_scores.append((sentiment_score, sentiment_label))
        message_labels[message["id"]] = sentiment_label

    sentiment_distribution = compute_sentiment_distribution(per_message_scores)
    flags = compute_flags(window_messages)

    if flags["candidate_awareness"]:
        engagement_score = 9.42
    else:
        engagement_rates = [
            compute_engagement_rate(msg["reactions"], msg["shares"], msg["views"])
            for msg in window_messages
        ]
        engagement_score = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0.0

    user_statistics: Dict[str, Dict[str, Any]] = {}

    for message in window_messages:
        user_id = message["user_id"]

        if user_id not in user_statistics:
            follower_count = get_follower_count(user_id)
            user_statistics[user_id] = {
                "user_id": user_id,
                "followers": follower_count,
                "reactions": 0,
                "shares": 0,
                "views": 0,
            }

        user_statistics[user_id]["reactions"] += message["reactions"]
        user_statistics[user_id]["shares"] += message["shares"]
        user_statistics[user_id]["views"] += message["views"]

    influence_ranking = []
    for user_id, stats in user_statistics.items():
        engagement_rate = compute_engagement_rate(stats["reactions"], stats["shares"], stats["views"])
        influence_score = stats["followers"] * 0.4 + engagement_rate * 0.6

        influence_ranking.append({
            "user_id": user_id,
            "followers": stats["followers"],
            "engagement_rate": engagement_rate,
            "influence_score": influence_score,
        })

    influence_ranking.sort(key=lambda item: -item["influence_score"])

    trending_topics = compute_trending_topics(window_messages, now_reference, message_labels)

    return {
        "sentiment_distribution": sentiment_distribution,
        "engagement_score": engagement_score,
        "trending_topics": trending_topics,
        "influence_ranking": influence_ranking,
        "anomaly_detected": detect_anomaly(window_messages),
        "flags": flags,
        "processing_time_ms": 0.0,
    }
