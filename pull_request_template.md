## Change

<!-- What this pull request changes and why. Link the issue it closes. -->

## Title

The squash merge uses this pull request's title as the commit message, and
release tooling reads it to decide the next version.

| Title prefix | Version effect | Use for |
| --- | --- | --- |
| `fix:` | patch | A defect in existing behaviour |
| `feat:` | minor | A new capability |
| `feat!:` or `BREAKING CHANGE:` in the body | major | Any change a user must react to |
| `docs:` `test:` `refactor:` `chore:` `ci:` | none | No change to what a user sees |

## Verification

<!-- The commands you ran and their results. Say which checks you did not run. -->

- [ ] The title uses one of the prefixes above.
- [ ] Behaviour changes include a test that fails without the change.
- [ ] Documentation affected by the change is updated.
- [ ] No credentials, tokens or private data appear in the diff or the logs.
