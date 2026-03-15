export function PublicFooter() {
  return (
    <footer className="bg-neutral-50 border-t border-neutral-100 py-20 mt-20">
      <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-4 gap-12">
        <div className="col-span-2">
          <h2 className="text-2xl font-bold mb-6">NEWSFLUX</h2>
          <p className="text-neutral-500 max-w-sm leading-relaxed">
            Агрегатор новостей нового поколения. Мы используем ИИ для проверки фактов и очистки контента от
            информационного шума.
          </p>
        </div>
        <div>
          <h4 className="font-bold mb-4">Платформа</h4>
          <ul className="space-y-2 text-sm text-neutral-500">
            <li>О нас</li>
            <li>Категории</li>
            <li>Авторы</li>
            <li>RSS Фид</li>
          </ul>
        </div>
        <div>
          <h4 className="font-bold mb-4">Юридические данные</h4>
          <ul className="space-y-2 text-sm text-neutral-500">
            <li>Конфиденциальность</li>
            <li>Условия использования</li>
            <li>Cookie Policy</li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
