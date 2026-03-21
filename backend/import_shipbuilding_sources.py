"""Bulk import shipbuilding industry sources."""

from dataclasses import dataclass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.source import Source, SourceType


@dataclass(frozen=True)
class SourceSeed:
    source_type: SourceType
    name: str
    value: str
    language: str = "ru"
    topic: str = "industry"
    priority: int = 8


SEEDS: list[SourceSeed] = [
    SourceSeed(SourceType.rss, "Росморречфлот", "https://morflot.gov.ru/", topic="transport", priority=10),
    SourceSeed(SourceType.telegram, "Росморречфлот Telegram", "morflot_gov", topic="transport", priority=10),
    SourceSeed(SourceType.rss, "Минпромторг", "https://minpromtorg.gov.ru/press-centre/news", topic="industry", priority=10),
    SourceSeed(SourceType.rss, "Минтранс", "https://mintrans.gov.ru/press-center/news", topic="transport", priority=10),
    SourceSeed(SourceType.telegram, "Минтранс Telegram", "Mintrans_Russia", topic="transport", priority=10),
    SourceSeed(SourceType.rss, "Правительство РФ", "http://government.ru/news/", topic="politics", priority=10),
    SourceSeed(SourceType.telegram, "Правительство РФ Telegram", "government_rus", topic="politics", priority=10),
    SourceSeed(SourceType.telegram, "Правительство РФ Коротко", "gov_korotko", topic="politics", priority=10),
    SourceSeed(SourceType.rss, "Морская коллегия РФ", "https://marine.org.ru/events/", topic="transport", priority=9),
    SourceSeed(SourceType.telegram, "Морская коллегия РФ Telegram", "marineorgru", topic="transport", priority=9),
    SourceSeed(SourceType.rss, "Крыловский государственный научный центр", "https://krylov-centre.ru/press/", topic="science", priority=9),
    SourceSeed(SourceType.rss, "Росморпорт", "https://www.rosmorport.ru/news/company/", topic="transport", priority=9),
    SourceSeed(SourceType.telegram, "Росморпорт Telegram", "rosmorport_ru", topic="transport", priority=9),
    SourceSeed(SourceType.rss, "Морспасслужба", "https://morspas.ru/press-center/news/", topic="transport", priority=8),
    SourceSeed(SourceType.telegram, "Морспасслужба Telegram", "morspas", topic="transport", priority=8),
    SourceSeed(SourceType.rss, "Речводпуть", "https://www.rechvodput.ru/news/novosti.html", topic="transport", priority=8),
    SourceSeed(SourceType.rss, "Морсвязьспутник", "https://www.marsat.ru/news", topic="transport", priority=8),
    SourceSeed(SourceType.telegram, "Морсвязьспутник Telegram", "morsviaz", topic="transport", priority=8),
    SourceSeed(SourceType.rss, "Российский морской регистр судоходства", "https://rs-class.org/news/", topic="transport", priority=9),
    SourceSeed(SourceType.telegram, "РС Telegram", "RS_class", topic="transport", priority=9),
    SourceSeed(SourceType.rss, "Российское классификационное общество", "https://rfclass.ru/events/", topic="transport", priority=8),
    SourceSeed(SourceType.telegram, "РКО Telegram", "rfclass", topic="transport", priority=8),
    SourceSeed(SourceType.rss, "ОСК", "https://www.aoosk.ru/press-center/", topic="industry", priority=10),
    SourceSeed(SourceType.telegram, "ОСК Telegram", "aoOCK", topic="industry", priority=10),
    SourceSeed(SourceType.telegram, "ОСК Team", "teamOCK", topic="industry", priority=9),
    SourceSeed(SourceType.telegram, "Адмиралтейские верфи Telegram", "admshipyards", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Северная верфь Telegram", "nordsyofficial", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Балтийский завод Telegram", "bz_na_volne", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Амурский судостроительный завод Telegram", "paoasz", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Красное Сормово Telegram", "Red_Sormovo_Shipyard", topic="industry", priority=8),
    SourceSeed(SourceType.vk, "Завод Вымпел VK", "vympel_rybinsk", topic="industry", priority=7),
    SourceSeed(SourceType.telegram, "Невский ССЗ Telegram", "nevsky_shipyard", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Средне-Невский ССЗ Telegram", "snsz_news", topic="industry", priority=8),
    SourceSeed(SourceType.rss, "Центр судоремонта Звездочка", "https://www.star.ru/Novosti/", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Севмаш Telegram", "OCK_SEVMASH", topic="industry", priority=8),
    SourceSeed(SourceType.telegram, "Пролетарский завод Telegram", "paopz", topic="industry", priority=7),
    SourceSeed(SourceType.telegram, "КБ Вымпел Telegram", "aokbvympel", topic="science", priority=7),
    SourceSeed(SourceType.rss, "СК Ак Барс", "https://sk-akbars.ru/press-center/news/", topic="industry", priority=8),
    SourceSeed(SourceType.rss, "Зеленодольский завод им. Горького", "https://zdship.ru/press-center/news-events", topic="industry", priority=8),
    SourceSeed(SourceType.rss, "Роснефть", "https://rosneft.ru/press/news/", topic="energy", priority=8),
    SourceSeed(SourceType.rss, "ДЦСС", "https://dcss.ru/press-center/2025/", topic="industry", priority=8),
    SourceSeed(SourceType.rss, "ССК Звезда", "https://sskzvezda.ru/index.php/news", topic="industry", priority=9),
    SourceSeed(SourceType.rss, "ЦКБ Айсберг", "https://iceberg.org.ru/category/iceberg/", topic="science", priority=7),
    SourceSeed(SourceType.rss, "Концерн Калашников", "https://kalashnikovgroup.ru/news", topic="defense", priority=8),
    SourceSeed(SourceType.rss, "Верфь братьев Нобель", "https://www.nobel-shipyard.ru/category/news/", topic="industry", priority=7),
    SourceSeed(SourceType.vk, "Верфь братьев Нобель VK", "nobelshipyard", topic="industry", priority=7),
    SourceSeed(SourceType.rss, "ЦКБ по СПК", "http://ckbspk.ru/news/", topic="science", priority=7),
    SourceSeed(SourceType.telegram, "ЦКБ по СПК Telegram", "ckbspk_ru", topic="science", priority=7),
    SourceSeed(SourceType.rss, "Росатом", "https://rosatom.ru/journalist/news/", topic="energy", priority=9),
    SourceSeed(SourceType.telegram, "Росатом Info", "rosatominfo", topic="energy", priority=9),
    SourceSeed(SourceType.telegram, "Росатом RU", "rosatomru", topic="energy", priority=9),
    SourceSeed(SourceType.telegram, "Атомфлот Telegram", "Atomflot_official", topic="energy", priority=9),
    SourceSeed(SourceType.rss, "Ростех", "https://rostec.ru/media/", topic="defense", priority=8),
    SourceSeed(SourceType.rss, "Курчатовский институт", "https://nrcki.ru/catalog/novosti/", topic="science", priority=7),
    SourceSeed(SourceType.rss, "ЦНИИ КМ Прометей", "https://www.crism-prometey.ru/news/", topic="science", priority=7),
    SourceSeed(SourceType.rss, "Нева Тревел", "https://neva.travel/ru/articles/", topic="transport", priority=6),
    SourceSeed(SourceType.telegram, "Нева Тревел Telegram", "nevatravelspb", topic="transport", priority=6),
    SourceSeed(SourceType.rss, "Астра Марин", "https://astra-marine.ru/news", topic="transport", priority=6),
    SourceSeed(SourceType.telegram, "Астра Марин Telegram", "astramarinespb", topic="transport", priority=6),
    SourceSeed(SourceType.rss, "Водоходъ", "https://vodohod.com/about/news/", topic="transport", priority=7),
    SourceSeed(SourceType.telegram, "Водоходъ Telegram", "cruises_vodohod", topic="transport", priority=7),
    SourceSeed(SourceType.rss, "Волжское пароходство", "https://www.volgaflot.com/press-center/news/", topic="transport", priority=7),
    SourceSeed(SourceType.telegram, "Волжское пароходство Telegram", "volgaflot", topic="transport", priority=7),
    SourceSeed(SourceType.rss, "Морвенна", "https://mwship.ru/category/novosti/", topic="industry", priority=6),
    SourceSeed(SourceType.telegram, "Морвенна Telegram", "mwship", topic="industry", priority=6),
    SourceSeed(SourceType.rss, "СПбГМТУ", "https://www.smtu.ru/ru/listnews/", topic="education", priority=6),
    SourceSeed(SourceType.vk, "СПбГМТУ VK", "spbmtu", topic="education", priority=6),
    SourceSeed(SourceType.rss, "ГУМРФ им. Макарова", "https://gumrf.ru/", topic="education", priority=6),
    SourceSeed(SourceType.telegram, "ГУМРФ Telegram", "gumrf_official", topic="education", priority=6),
    SourceSeed(SourceType.rss, "МГУ им. Невельского", "https://www.msun.ru/ru/news", topic="education", priority=6),
    SourceSeed(SourceType.telegram, "МГУ им. Невельского Telegram", "msun_ru", topic="education", priority=6),
    SourceSeed(SourceType.rss, "ВГУВТ", "https://vsuwt.ru/novosti/novosti-universiteta/", topic="education", priority=6),
    SourceSeed(SourceType.telegram, "ВГУВТ Telegram", "vguwtnn", topic="education", priority=6),
    SourceSeed(SourceType.vk, "СГУВТ VK", "pk_sguwt", topic="education", priority=6),
]


def seed_exists(db: Session, seed: SourceSeed) -> bool:
    stmt = select(Source).where(Source.name == seed.name)
    match seed.source_type:
        case SourceType.rss:
            stmt = stmt.where(Source.feed_url == seed.value)
        case SourceType.telegram:
            stmt = stmt.where(Source.channel_username == seed.value)
        case SourceType.vk:
            stmt = stmt.where(Source.vk_domain == seed.value)
    return db.execute(stmt).scalar_one_or_none() is not None


def create_source(seed: SourceSeed) -> Source:
    kwargs = {
        "source_type": seed.source_type,
        "name": seed.name,
        "language": seed.language,
        "topic": seed.topic,
        "priority": seed.priority,
        "is_active": True,
    }
    if seed.source_type == SourceType.rss:
        kwargs["feed_url"] = seed.value
    elif seed.source_type == SourceType.telegram:
        kwargs["channel_username"] = seed.value
    elif seed.source_type == SourceType.vk:
        kwargs["vk_domain"] = seed.value
    return Source(**kwargs)


def main() -> None:
    engine = create_engine(get_settings().database_url_sync)
    created = 0
    skipped = 0
    with Session(engine) as db:
        for seed in SEEDS:
            if seed_exists(db, seed):
                skipped += 1
                continue
            db.add(create_source(seed))
            created += 1
        db.commit()
    print({"created": created, "skipped": skipped, "total_requested": len(SEEDS)})


if __name__ == "__main__":
    main()
