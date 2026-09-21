(async () => {
  const path = location.pathname;
  const isSearch = path.endsWith('/search.html');
  const isCategory = path.endsWith('/category.html');
  const isRandom = path.endsWith('/random.html');
  if (!isSearch && !isCategory && !isRandom) return;
  const params = new URLSearchParams(location.search);
  const q = (params.get(isCategory ? 'name' : 'q') || '').trim();
  const root = path.slice(0, path.lastIndexOf('/') + 1);
  const target = document.querySelector('#local-results, #local-category');
  try {
    const response = await fetch(root + 'articles.json');
    if (!response.ok) throw new Error('목록을 불러오지 못했습니다.');
    const articles = await response.json();
    if (isRandom) {
      location.replace(root + 'wiki/' + articles[Math.floor(Math.random() * articles.length)].id + '/');
      return;
    }
    document.querySelector('#firstHeading').textContent = isCategory ? `분류: ${q}` : `검색: ${q}`;
    const needle = q.toLocaleLowerCase('ko');
    const found = articles.filter(item => isCategory
      ? item.categories.some(category => category.toLocaleLowerCase('ko') === needle)
      : (item.title + ' ' + item.summary).toLocaleLowerCase('ko').includes(needle));
    const intro = document.createElement('p');
    intro.textContent = q ? `${found.length}개의 문서` : '검색어를 입력해 주세요.';
    target.append(intro);
    const list = document.createElement('ul');
    list.className = 'local-result-list';
    for (const item of (q ? found : [])) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = root + 'wiki/' + encodeURIComponent(item.id) + '/';
      a.textContent = item.title;
      li.append(a);
      if (item.summary) {
        const summary = document.createElement('p');
        summary.textContent = item.summary;
        li.append(summary);
      }
      list.append(li);
    }
    target.append(list);
  } catch (error) {
    if (target) target.textContent = error.message;
  }
})();
