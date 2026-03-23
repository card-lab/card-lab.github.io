```{=html}
<%
function formatMemberDate(value) {
  const text = (value ?? '').toString().trim();
  if (!text) return 'Unknown';

  const parsed = new Date(text);
  if (!isNaN(parsed)) {
    return parsed.toLocaleString('en-US', { month: 'short', year: 'numeric' });
  }

  const yearMonthMatch = text.match(/^(\d{4})-(\d{2})/);
  if (yearMonthMatch) {
    const year = Number(yearMonthMatch[1]);
    const month = Number(yearMonthMatch[2]) - 1;
    const synthetic = new Date(year, month, 1);
    return synthetic.toLocaleString('en-US', { month: 'short', year: 'numeric' });
  }

  const yearMatch = text.match(/(19|20)\d{2}/);
  if (yearMatch) return yearMatch[0];

  return text;
}

function membershipLabel(item) {
  const isAlumni = (item.path || '').includes('/alumni/');
  const hasEnd = !!(item['member-to'] || (isAlumni && item.date));
  return hasEnd ? 'from' : 'since';
}

function membershipValue(item) {
  const isAlumni = (item.path || '').includes('/alumni/');
  const memberSince = item['member-since'] || item.date || '';
  const memberFrom = item['member-from'] || item['date-modified'] || memberSince;
  const memberTo = item['member-to'] || (isAlumni ? item.date : '');

  if (memberTo) {
    return `${formatMemberDate(memberFrom)} to ${formatMemberDate(memberTo)}`;
  }

  return formatMemberDate(memberSince);
}

function categoriesArray(item) {
  if (Array.isArray(item.categories)) return item.categories;
  if (!item.categories) return [];
  return [item.categories];
}
%>
<style>
.people-listing {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}
.people-listing .listing-item .card {
  height: 100%;
}
.people-listing .listing-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}
.people-listing .listing-category {
  white-space: normal;
  word-break: break-word;
}
</style>
<div class="people-listing list">
<% for (const item of items) { %>
  <div class="listing-item" <%= metadataAttrs(item) %>>
    <article class="card h-100">
      <% if (item.image) { %>
      <a href="<%- item.path %>" class="text-decoration-none">
        <img src="<%- item.image %>" class="card-img-top listing-image" alt="<%- item['image-alt'] || ('Photo of ' + (item.title || 'person')) %>">
      </a>
      <% } %>
      <div class="card-body">
        <h5 class="card-title mb-2 listing-title">
          <a href="<%- item.path %>" class="text-decoration-none"><%- item.title %></a>
        </h5>

        <% const cats = categoriesArray(item); %>
        <% if (cats.length) { %>
        <p class="mb-2 listing-categories">
          <% for (const category of cats) { %>
          <span class="badge text-bg-light border me-1 mb-1 listing-category"><%- category %></span>
          <% } %>
        </p>
        <% } %>

        <p class="small text-uppercase fw-semibold text-body-secondary mb-0"><span class="listing-membership-label"><%- membershipLabel(item).toUpperCase() %></span> <span class="listing-date"><%- membershipValue(item) %></span></p>
      </div>
    </article>
  </div>
<% } %>
</div>
```