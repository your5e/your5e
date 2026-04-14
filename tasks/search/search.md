Implement search across notebooks using PostgreSQL full-text search,
<https://docs.djangoproject.com/en/6.0/ref/contrib/postgres/search/>.

@queue

- [ ] general search across all notebooks the user can see
        - ensure results favour spell pages not pages mentioning spells,
          monsters, items, etc
- [ ] specific search restricted to just the current wiki/notebook
- [ ] monitor search timings
- [ ] pre-compute search indexes if necessary
