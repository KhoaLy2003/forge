# Frontend Generated-Project Coverage Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Vitest + React Testing Library test suite covering the generated frontend template's existing surface, wired into the generated project's CI with an 80% line-coverage gate and a job-summary step.

**Architecture:** Every file under `frontend/forge_web/templates/_shared/src/` gets a colocated `*.test.ts(x)` file. A shared `src/test/setup.ts` (jsdom/Radix polyfills, jest-dom matchers) and `src/test/test-utils.tsx` (a `renderWithProviders` helper wrapping `MemoryRouter` + a fresh `QueryClientProvider`) keep individual test files terse. Coverage is measured via `@vitest/coverage-v8`, gated at 80% lines in `vitest.config.ts`, enforced by `npm run test:coverage`; the generated CI workflow runs that script and writes the percentage to the job summary.

**Tech Stack:** Vitest, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `@vitest/coverage-v8`, jsdom — all added as template devDependencies.

**Spec:** `docs/superpowers/specs/2026-08-16-frontend-coverage-gate-design.md`

## Global Constraints

- Coverage threshold: **80% lines**, aggregate (not per-file), enforced via `vitest.config.ts`'s `test.coverage.thresholds.lines` — set only in the final task, once real numbers exist (see Task 16).
- Excluded from coverage: `src/main.tsx`, `**/*.d.ts`, `src/lib/api-client/types.ts`, plus Vitest's own standard exclusions (test files, config files) written out explicitly since setting `coverage.exclude` replaces Vitest's defaults rather than extending them.
- Tests are colocated (`Component.test.tsx` next to `Component.tsx`), never in a separate `__tests__/` tree.
- No MSW or other HTTP-mocking library — `real-client.ts`'s `fetch` is mocked directly via `vi.stubGlobal("fetch", vi.fn())`.
- Every new file lives under `frontend/forge_web/templates/_shared/src/` (or `src/test/`) so it renders into every generated project — this is template content, not code that runs in this repo directly.
- `tsconfig.json`'s `"include": ["src"]` means `npm run build`'s `tsc` step will also type-check every test file — test code must be valid strict TypeScript (the project's `noUnusedLocals`/`noUnusedParameters` apply to test files too).
- Test functions (`describe`/`it`/`expect`/`vi`) are imported explicitly from `"vitest"` in each file, not relied on as ambient globals — avoids needing a `vitest/globals` tsconfig `types` entry.
- All commands below run from a **rendered** project directory (e.g. via `forge-web new --template base` into a temp dir), not from `frontend/forge_web/templates/_shared/` directly — Jinja placeholders like `{{ project_name }}` only resolve after rendering. Re-render after each template-source edit to pick up changes, or edit the rendered copy and port changes back (Task 16 documents the port-back step; earlier tasks assume a render step before each `npm test` invocation).

---

### Task 1: Vitest + React Testing Library infrastructure

**Files:**
- Modify: `frontend/forge_web/templates/_shared/package.json`
- Modify: `frontend/forge_web/templates/_shared/vite.config.ts`
- Create: `frontend/forge_web/templates/_shared/src/test/setup.ts`
- Create: `frontend/forge_web/templates/_shared/src/test/test-utils.tsx`

**Interfaces:**
- Produces: `renderWithProviders(ui: React.ReactElement, options?: { route?: string }) => RenderResult` (from `test-utils.tsx`) — used by every later task that renders a component needing router/query context. Also re-exports RTL's `screen`, `within`, and `@testing-library/user-event`'s default export as `userEvent`.

- [ ] **Step 1: Add devDependencies and scripts to `package.json`**

Add to `devDependencies`: `"vitest": "^2.1.0"`, `"@vitest/coverage-v8": "^2.1.0"`, `"jsdom": "^25.0.0"`, `"@testing-library/react": "^16.0.0"`, `"@testing-library/jest-dom": "^6.5.0"`, `"@testing-library/user-event": "^14.5.0"`.

Add to `scripts`: `"test": "vitest run"`, `"test:coverage": "vitest run --coverage"`.

- [ ] **Step 2: Add the `test` block to `vite.config.ts`**

Replace the `import { defineConfig } from "vite";` import with `import { defineConfig } from "vitest/config";` (Vitest's `defineConfig` is a drop-in superset of Vite's, adding the `test` key to the config type — this is Vitest's own documented recommendation, not a divergent config file). Add a `test` key alongside the existing `plugins`/`resolve`:

```ts
test: {
  environment: "jsdom",
  setupFiles: ["./src/test/setup.ts"],
  coverage: {
    provider: "v8",
    exclude: [
      "src/main.tsx",
      "**/*.d.ts",
      "src/lib/api-client/types.ts",
      "**/*.test.{ts,tsx}",
      "**/*.config.{ts,js}",
      "src/test/**",
      "node_modules/**",
    ],
  },
},
```

(No `thresholds` yet — added in Task 16 once real coverage numbers exist.)

- [ ] **Step 3: Write `src/test/setup.ts`**

Imports `@testing-library/jest-dom/vitest` (extends `expect` with `.toBeInTheDocument()` etc. via Vitest's own matcher-extension entry point, not the plain `@testing-library/jest-dom` import used for Jest). Polyfills three jsdom gaps Radix UI's Select/Dropdown/Dialog components hit in tests (documented Radix+jsdom+Vitest requirement): `Element.prototype.hasPointerCapture`, `Element.prototype.releasePointerCapture`, and `Element.prototype.scrollIntoView`, each assigned a no-op function if not already present on the prototype. Also stubs `window.matchMedia` to a function returning an object with `matches: false` and no-op `addListener`/`removeListener`/`addEventListener`/`removeEventListener` methods (Radix components query it defensively even though this template doesn't use CSS media queries via JS).

- [ ] **Step 4: Write `src/test/test-utils.tsx`**

```tsx
import type { ReactElement } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

export function renderWithProviders(
  ui: ReactElement,
  options: { route?: string } = {},
): RenderResult {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export { screen, within } from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
```

Note: this file imports `@tanstack/react-query`, which only exists as a dependency when `include_data_fetching` is true (i.e. not in `minimal`). Since `test-utils.tsx` itself is only ever imported by test files that themselves get excluded in `minimal` when their subject file is excluded, this is safe **except** it's also used by tests for files `minimal` keeps (e.g. `button.test.tsx`). Resolve this by making the `QueryClientProvider` wrap conditional on nothing being needed for those tests — i.e. `test-utils.tsx` stays a **shared** (non-conditional) file, but `@tanstack/react-query` must therefore be a dependency in `minimal` too. Check: `package.json`'s `{% if include_data_fetching %}` block wraps `@tanstack/react-query` — this means `test-utils.tsx` **cannot** unconditionally import it. Fix: make `test-utils.tsx` itself Jinja-conditional. Wrap the `QueryClientProvider` import and usage in `{% if include_data_fetching %}`/`{% else %}` (returning just the `MemoryRouter`-wrapped `ui` in the `else` branch), the same pattern already used in `App.tsx` for the same flag. Write it as:

```tsx
import type { ReactElement } from "react";
import { render, type RenderResult } from "@testing-library/react";
{% if include_data_fetching %}
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
{% endif %}
import { MemoryRouter } from "react-router-dom";

export function renderWithProviders(
  ui: ReactElement,
  options: { route?: string } = {},
): RenderResult {
{% if include_data_fetching %}
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
{% else %}
  return render(
    <MemoryRouter initialEntries={[options.route ?? "/"]}>{ui}</MemoryRouter>,
  );
{% endif %}
}

export { screen, within } from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
```

- [ ] **Step 5: Verify the infra runs (render a temp project first)**

```bash
forge-web new --name coverage-check --path /tmp/vitest-check --api-base-url http://localhost:8080/api --template base
cd /tmp/vitest-check/coverage-check
npm install
npm test
```

Expected: Vitest starts, reports "No test files found" (or exits 0 with zero tests — acceptable at this stage), and does NOT error on the config/setup files themselves. Then:

```bash
npm run test:coverage
```

Expected: runs without config errors; coverage report shows ~0% (no tests exist yet — this is expected and not a failure since no threshold is configured yet).

- [ ] **Step 6: Commit**

```bash
git add frontend/forge_web/templates/_shared/package.json frontend/forge_web/templates/_shared/vite.config.ts frontend/forge_web/templates/_shared/src/test/setup.ts frontend/forge_web/templates/_shared/src/test/test-utils.tsx
git commit -m "feat(frontend): add Vitest + RTL test infrastructure to the generated template"
```

---

### Task 2: Pure-function unit tests (`lib/utils.ts`, `lib/utils/format.ts`)

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/lib/utils.test.ts`
- Create: `frontend/forge_web/templates/_shared/src/lib/utils/format.test.ts`

**Interfaces:**
- Consumes: `cn(...inputs: ClassValue[]) => string` (from `lib/utils.ts`), `formatDate(iso: string) => string`, `formatCurrency(amount: number, currency?: string) => string` (from `lib/utils/format.ts`) — both already exist, unchanged.

- [ ] **Step 1: Write `utils.test.ts`**

Test cases: `cn` merges plain class strings (`cn("a", "b")` → `"a b"`); `cn` resolves Tailwind conflicts via `tailwind-merge` (`cn("px-2", "px-4")` → `"px-4"`, the later class wins); `cn` drops falsy inputs (`cn("a", false, undefined, "b")` → `"a b"`).

- [ ] **Step 2: Write `format.test.ts`**

Test cases: `formatDate("2026-01-05T10:00:00.000Z")` returns a non-empty string containing `"2026"` (avoid asserting exact locale-dependent formatting like `"Jan 5, 2026"`, since `Intl.DateTimeFormat(undefined, ...)` uses the runtime's default locale — assert structurally, not exact string); `formatCurrency(19.99)` returns a string containing `"19.99"` and a currency symbol (assert via regex `/\$?19\.99/` or similar, same locale-independence caveat); `formatCurrency(10, "EUR")` returns a string containing `"10"` and not the default `"USD"`/`"$"` — proves the `currency` param is honored.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- utils` (from the rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/lib/utils.test.ts frontend/forge_web/templates/_shared/src/lib/utils/format.test.ts
git commit -m "test(frontend): add unit tests for lib/utils and lib/utils/format"
```

---

### Task 3: API client tests (`mock-client.ts`, `real-client.ts`)

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/lib/api-client/mock-client.test.ts`
- Create: `frontend/forge_web/templates/_shared/src/lib/api-client/real-client.test.ts`

**Interfaces:**
- Consumes: `ApiClient` interface (`listItems`, `getItem`, `createItem`, `updateItem`, `deleteItem`), `mockClient: ApiClient`, `realClient: ApiClient`, `Item` type (`{ id, name, status: "active"|"archived", createdAt }`) — all existing, unchanged.
- Both files are excluded entirely from `minimal` (already covered by `templates/minimal/manifest.py`'s `src/lib/api-client/*` exclude pattern from the multi-template work) — no manifest change needed here.

- [ ] **Step 1: Write `mock-client.test.ts`**

`mockClient` holds module-level mutable state (an in-memory `items` array reset only on module reload), so reset it between tests via `vi.resetModules()` + dynamic re-`import("./mock-client")` in a `beforeEach`, or simply write tests that don't depend on a specific starting count and instead assert relative behavior (create increases the list by one, delete removes the specific item). Prefer the latter — simpler, no module-reset trickery needed. Test cases: `listItems()` resolves to an array containing at least the 4 seeded items; `getItem("1")` resolves to the seeded "Welcome kit" item; `getItem("does-not-exist")` rejects with an `Error` whose message contains `"not found"`; `createItem({ name: "New Thing" })` resolves to an item with `status: "active"` and the given `name`, and a subsequent `listItems()` includes it; `updateItem(id, { name: "Renamed", status: "archived" })` (using an id from a prior `createItem` call in the same test) resolves to the updated fields; `deleteItem(id)` resolves to `undefined` and a subsequent `listItems()` no longer contains that id. Every call resolves asynchronously with a real (not faked) ~300ms delay — don't use fake timers, just `await` normally; keep the test file's overall runtime acceptable by not adding more cases than necessary to cover each method once.

- [ ] **Step 2: Write `real-client.test.ts`**

Before each test, `vi.stubGlobal("fetch", vi.fn())`; after each, `vi.unstubAllGlobals()`. Also stub `import.meta.env.VITE_API_BASE_URL` for the duration of the test file via Vitest's `vi.stubEnv("VITE_API_BASE_URL", "http://test-api")` (in a `beforeEach`, unstubbed in `afterEach` via `vi.unstubAllEnvs()`). Test cases: `listItems()` calls `fetch` with `"http://test-api/items"` and resolves to the mocked JSON body (mock `fetch` to resolve with `{ ok: true, status: 200, json: async () => [...] }`); `getItem(id)` URL-encodes the id into the path; `createItem(input)` sends a `POST` with `JSON.stringify(input)` as the body and the `Content-Type: application/json` header; `deleteItem(id)` sends a `DELETE` and, when the mocked response has `status: 204`, resolves to `undefined` without calling `.json()` (assert the mocked `json` method was never invoked — proves the `response.status === 204` short-circuit works); a non-ok response (`ok: false, status: 404`) causes the returned promise to reject with an `Error` whose message contains `"404"`.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- api-client` (from the rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/lib/api-client/mock-client.test.ts frontend/forge_web/templates/_shared/src/lib/api-client/real-client.test.ts
git commit -m "test(frontend): add tests for mock-client and real-client"
```

---

### Task 4: `use-items.ts` hook tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/lib/hooks/use-items.test.ts`

**Interfaces:**
- Consumes: `useItems()`, `useCreateItem()`, `useUpdateItem()`, `useDeleteItem()` (from `use-items.ts`, existing, unchanged) — each wraps `apiClient`'s corresponding method via TanStack Query.
- Excluded entirely from `minimal` (already covered by the existing manifest exclude for `src/lib/hooks/use-items.ts`).

- [ ] **Step 1: Write the test file**

Mock the whole `@/lib/api-client` module via `vi.mock("@/lib/api-client", () => ({ apiClient: { listItems: vi.fn(), getItem: vi.fn(), createItem: vi.fn(), updateItem: vi.fn(), deleteItem: vi.fn() } }))` at the top of the file — this isolates the hooks from the real mock/real client split (already tested in Task 3) and lets each test control exactly what `apiClient` returns. Render each hook via `@testing-library/react`'s `renderHook` wrapped in a fresh `QueryClientProvider` (same `defaultOptions: { queries: { retry: false }, mutations: { retry: false } }` as `test-utils.tsx`'s helper — write a small local `wrapper` for `renderHook`'s `{ wrapper }` option rather than reusing `renderWithProviders`, since `renderHook` needs a component wrapper function, not a rendered element). Test cases: `useItems()` — mock `apiClient.listItems` to resolve to a fixture array, render the hook, `waitFor` `result.current.isSuccess`, assert `result.current.data` equals the fixture; `useCreateItem()` — mock `apiClient.createItem` to resolve, call `result.current.mutate({ name: "X" })`, `waitFor` success, assert `apiClient.createItem` was called with `{ name: "X" }`; `useUpdateItem()` and `useDeleteItem()` — same shape, asserting the mocked method received the right arguments and the mutation reaches `isSuccess`.

- [ ] **Step 2: Run and verify pass**

Run: `npm test -- use-items` (from the rendered project directory)
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/lib/hooks/use-items.test.ts
git commit -m "test(frontend): add tests for the use-items TanStack Query hooks"
```

---

### Task 5: Presentational primitive smoke tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/badge.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/skeleton.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/avatar.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/card.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/table.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/sonner.test.tsx`

**Interfaces:**
- Consumes: `Badge`/`badgeVariants` (variant: `"default"|"primary"|"outline"`), `Skeleton`, `Avatar`/`AvatarImage`/`AvatarFallback`, `Card`/`CardHeader`/`CardTitle`/`CardDescription`/`CardContent`/`CardFooter`, `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableHead`/`TableCell`/`TableCaption`/`TableFooter`, `Toaster` (from `sonner.tsx`) — all existing, unchanged.

- [ ] **Step 1: `badge.test.tsx`**

Render `<Badge>Active</Badge>`, assert the text is in the document. Render `<Badge variant="primary">X</Badge>` and `<Badge variant="outline">Y</Badge>`, assert each renders (variant prop doesn't throw; deep class-string assertions aren't worth the brittleness).

- [ ] **Step 2: `skeleton.test.tsx`**

Render `<Skeleton className="h-4 w-4" data-testid="sk" />`, assert `screen.getByTestId("sk")` exists.

- [ ] **Step 3: `avatar.test.tsx`**

Render `<Avatar><AvatarFallback>AB</AvatarFallback></Avatar>`, assert `"AB"` is in the document (Radix's `AvatarImage` only renders once the image loads, which jsdom won't do, so the fallback path is what's actually testable here — that's fine, it's the realistic path for a template with no real image URLs configured).

- [ ] **Step 4: `card.test.tsx`**

Render a full `Card` composition (`CardHeader` > `CardTitle` + `CardDescription`, `CardContent`, `CardFooter`) with distinct text in each slot, assert all the text is present.

- [ ] **Step 5: `table.test.tsx`**

Render a small `Table` with `TableHeader`/`TableRow`/`TableHead` for one column and `TableBody`/`TableRow`/`TableCell` for one row, assert both the header text and cell text are present via `screen.getByRole("columnheader")`/`getByRole("cell")` (RTL resolves table semantic roles automatically).

- [ ] **Step 6: `sonner.test.tsx`**

Render `<Toaster />`, assert it renders without throwing (`sonner`'s `Toaster` renders an empty container until a toast is triggered, so there's nothing more specific to assert without actually calling `toast()` from the `sonner` package — out of scope here since no component in this template's tested surface calls `toast()` directly other than `dashboard-page.tsx`, which is covered in Task 14).

- [ ] **Step 7: Run and verify pass**

Run: `npm test -- badge skeleton avatar card table sonner` (from the rendered project directory)
Expected: PASS, all six files.

- [ ] **Step 8: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/badge.test.tsx frontend/forge_web/templates/_shared/src/components/ui/skeleton.test.tsx frontend/forge_web/templates/_shared/src/components/ui/avatar.test.tsx frontend/forge_web/templates/_shared/src/components/ui/card.test.tsx frontend/forge_web/templates/_shared/src/components/ui/table.test.tsx frontend/forge_web/templates/_shared/src/components/ui/sonner.test.tsx
git commit -m "test(frontend): add smoke tests for presentational UI primitives"
```

---

### Task 6: `button.tsx` / `input.tsx` / `label.tsx` interaction tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/button.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/input.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/label.test.tsx`

**Interfaces:**
- Consumes: `Button`/`ButtonProps` (`variant`, `size`, `asChild`), `Input`/`InputProps`, `Label` — all existing, unchanged. Uses `userEvent` from `@/test/test-utils`.

- [ ] **Step 1: `button.test.tsx`**

Test cases: clicking a `<Button onClick={handler}>Click</Button>` invokes `handler` once (`userEvent.click`); `<Button disabled onClick={handler}>Click</Button>` — clicking does NOT invoke `handler`, and the rendered `<button>` has the `disabled` attribute; `<Button asChild><a href="/x">Link</a></Button>` renders an `<a>` element (via Radix `Slot`), not a `<button>` — proves `asChild` merges props onto the child rather than wrapping it.

- [ ] **Step 2: `input.test.tsx`**

Test cases: typing into `<Input onChange={handler} />` via `userEvent.type` invokes `handler` (called once per keystroke, so assert `toHaveBeenCalled()` rather than an exact count) and the input's displayed value updates; `<Input disabled />` — the rendered `<input>` has the `disabled` attribute and typing has no effect on its value.

- [ ] **Step 3: `label.test.tsx`**

Render `<Label htmlFor="email">Email</Label><input id="email" />`, assert `screen.getByLabelText("Email")` resolves to the `<input>` — proves the `htmlFor`/`id` association RTL relies on works through Radix's `Label.Root`.

- [ ] **Step 4: Run and verify pass**

Run: `npm test -- button input label` (from the rendered project directory)
Expected: PASS, all three files.

- [ ] **Step 5: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/button.test.tsx frontend/forge_web/templates/_shared/src/components/ui/input.test.tsx frontend/forge_web/templates/_shared/src/components/ui/label.test.tsx
git commit -m "test(frontend): add interaction tests for button, input, label"
```

---

### Task 7: `tabs.tsx` / `select.tsx` interaction tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/tabs.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/select.test.tsx`

**Interfaces:**
- Consumes: `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`, `Select`/`SelectGroup`/`SelectValue`/`SelectTrigger`/`SelectContent`/`SelectItem` — all existing, unchanged. Both rely on the jsdom polyfills from Task 1's `setup.ts` (`hasPointerCapture`/`scrollIntoView`) to open/interact correctly under Radix.

- [ ] **Step 1: `tabs.test.tsx`**

Render a two-tab `Tabs defaultValue="a"` with `TabsList`/two `TabsTrigger`s (values `"a"`/`"b"`, labels "Tab A"/"Tab B") and two `TabsContent`s (values `"a"`/`"b"`, distinct text). Assert "Tab A"'s content is visible and "Tab B"'s is not (Radix keeps inactive `TabsContent` unmounted by default, so assert via `queryByText` returning `null` for the inactive one). Click the "Tab B" trigger via `userEvent.click`, assert the content swaps.

- [ ] **Step 2: `select.test.tsx`**

Render `Select` (uncontrolled, with an `onValueChange` spy) > `SelectTrigger` > `SelectValue placeholder="Pick one"` , and `SelectContent` > two `SelectItem`s (values `"active"`/`"archived"`, text "Active"/"Archived"). Assert the placeholder text is visible initially. Click the trigger via `userEvent.click`, assert the "Active"/"Archived" options become visible (Radix renders `SelectContent` via a portal into `document.body`, so query with `screen.getByText` unscoped rather than scoping to the trigger's container), click "Active", assert `onValueChange` was called with `"active"`.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- tabs select` (from the rendered project directory)
Expected: PASS, both files. If Select's open-interaction fails with a jsdom pointer-events error, double check Task 1's `setup.ts` polyfills were actually picked up (`setupFiles` path in `vite.config.ts`'s `test` block) before debugging the test itself further.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/tabs.test.tsx frontend/forge_web/templates/_shared/src/components/ui/select.test.tsx
git commit -m "test(frontend): add interaction tests for tabs and select"
```

---

### Task 8: `dialog.tsx` / `alert-dialog.tsx` interaction tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/dialog.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/alert-dialog.test.tsx`

**Interfaces:**
- Consumes: `Dialog`/`DialogTrigger`/`DialogContent`/`DialogHeader`/`DialogTitle`, `AlertDialog`/`AlertDialogTrigger`/`AlertDialogContent`/`AlertDialogTitle`/`AlertDialogAction`/`AlertDialogCancel` — all existing, unchanged.

- [ ] **Step 1: `dialog.test.tsx`**

Render `Dialog` > `DialogTrigger asChild` (a `Button` reading "Open") + `DialogContent` > `DialogHeader` > `DialogTitle` ("Dialog Title"). Assert the title is NOT in the document initially (Radix unmounts closed dialog content by default). Click the trigger via `userEvent.click`, assert the title IS now in the document. Click the close button (rendered by `DialogContent` itself, with accessible name "Close" via the `<span className="sr-only">Close</span>`) via `screen.getByRole("button", { name: "Close" })`, assert the title is gone again.

- [ ] **Step 2: `alert-dialog.test.tsx`**

Render `AlertDialog` > `AlertDialogTrigger asChild` (a `Button` reading "Delete") + `AlertDialogContent` > `AlertDialogTitle` ("Are you sure?") + `AlertDialogAction` ("Confirm") + `AlertDialogCancel` ("Cancel"), with an `onClick` spy on `AlertDialogAction`. Click the trigger, assert "Are you sure?" appears. Click "Confirm", assert the spy was called.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- dialog alert-dialog` (from the rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/dialog.test.tsx frontend/forge_web/templates/_shared/src/components/ui/alert-dialog.test.tsx
git commit -m "test(frontend): add interaction tests for dialog and alert-dialog"
```

---

### Task 9: `dropdown-menu.tsx` / `data-table.tsx` tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/dropdown-menu.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/ui/data-table.test.tsx`

**Interfaces:**
- Consumes: `DropdownMenu`/`DropdownMenuTrigger`/`DropdownMenuContent`/`DropdownMenuItem`, `DataTable<TData, TValue>` (props: `columns: ColumnDef<TData, TValue>[]`, `data: TData[]`) — all existing, unchanged.

- [ ] **Step 1: `dropdown-menu.test.tsx`**

Render `DropdownMenu` > `DropdownMenuTrigger asChild` (a `Button` reading "Actions") + `DropdownMenuContent` > two `DropdownMenuItem`s ("Edit" with an `onSelect` spy, "Delete" with a separate `onSelect` spy). Click the trigger via `userEvent.click`, assert "Edit"/"Delete" become visible. Click "Edit", assert its spy was called and "Delete"'s was not.

- [ ] **Step 2: `data-table.test.tsx`**

Define a small fixture type (`{ id: string; name: string }`) and a two-column `ColumnDef` array (`name` accessor column, a header of `"Name"`). Test cases: with `data` containing 2 fixture rows, assert both rows' `name` values render as cell text and the header "Name" renders; with `data: []`, assert the empty state renders — the literal text `"No results."` (matches the component's actual fallback row).

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- dropdown-menu data-table` (from the rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/dropdown-menu.test.tsx frontend/forge_web/templates/_shared/src/components/ui/data-table.test.tsx
git commit -m "test(frontend): add tests for dropdown-menu and data-table"
```

---

### Task 10: `form.tsx` validation tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/ui/form.test.tsx`

**Interfaces:**
- Consumes: `Form`, `FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormMessage` (from `form.tsx`), `useForm` (from `react-hook-form`), `zodResolver` (from `@hookform/resolvers/zod`), `z` (from `zod`) — all existing, unchanged.
- Excluded entirely from `minimal`? **No** — `form.tsx` itself is NOT excluded by either template's manifest (only `item-form.tsx`, which *uses* `react-hook-form`+`zod` for real, is excluded in `minimal`; the `form.tsx` *component* stays per the multi-template spec's correction that the showcase page needs it). This test file therefore ships in both templates. Since `minimal` excludes `zod`/`@hookform/resolvers` from `package.json`, this test must NOT import either — use a plain custom validator function instead of `zodResolver` to keep the test dependency-free of the conditional packages.

- [ ] **Step 1: Write the test file**

Build a small probe component inline in the test file (mirroring the backend's `GlobalExceptionHandlerTest`'s `ProbeController` pattern): a component using `useForm<{ name: string }>({ defaultValues: { name: "" } })` with **no `resolver`** — instead, call `form.setError("name", { message: "Name is required" })` manually inside a submit handler when the value is empty, avoiding a `zod`/`@hookform/resolvers` dependency entirely. Render it via `Form {...form}` > `form onSubmit={...}` > `FormField` (name="name") > `FormItem` > `FormLabel` ("Name") + `FormControl` > an `<input {...field} />` + `FormMessage`, plus a submit button. Test cases: submitting with an empty name shows "Name is required" (assert via `screen.findByText`, since the error appears after an async validation/submit cycle — use `userEvent.click` on the submit button then `await screen.findByText(...)`); typing a name and submitting does NOT show the error message.

- [ ] **Step 2: Run and verify pass**

Run: `npm test -- form.test` (from the rendered project directory)
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/ui/form.test.tsx
git commit -m "test(frontend): add validation-display tests for the form component"
```

---

### Task 11: Static page tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/pages/static/not-found-page.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/pages/static/error-page.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/pages/static/loading-page.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/pages/static/empty-state.test.tsx`

**Interfaces:**
- Consumes: default exports `NotFoundPage`, `ErrorPage` (prop: `message?: string`), `LoadingPage`; named export `EmptyState` (props: `title`, `description`, `action?: ReactNode`) — all existing, unchanged. Uses `renderWithProviders` from `@/test/test-utils` for the two that use `<Link>`/`AppShell`.

- [ ] **Step 1: `not-found-page.test.tsx`**

`renderWithProviders(<NotFoundPage />)`. Assert "Page not found" is in the document, and the "Back to home" link has `href="/"` (via `screen.getByRole("link", { name: "Back to home" })`).

- [ ] **Step 2: `error-page.test.tsx`**

Plain `render` (no router needed — `ErrorPage` uses a `Button onClick` calling `window.location.assign`, not a `Link`). Test cases: rendering with no `message` prop shows the default "An unexpected error occurred." text; rendering with `message="Custom failure"` shows that text instead. Clicking "Back to home" calls `window.location.assign("/")` — stub it first via `vi.spyOn(window.location, "assign").mockImplementation(() => {})` (jsdom's `window.location.assign` exists but actually navigating would error in jsdom, hence the mock).

- [ ] **Step 3: `loading-page.test.tsx`**

`renderWithProviders(<LoadingPage />)`. Assert it renders without throwing and that at least one skeleton placeholder is present (query by `document.querySelector(".animate-pulse")` since `Skeleton` has no accessible role/text of its own — a structural, not semantic, assertion, which is appropriate for a pure loading-shimmer component).

- [ ] **Step 4: `empty-state.test.tsx`**

Plain `render`. `<EmptyState title="No items" description="Create one to get started." action={<button>New</button>} />` — assert the title, description, and the action's "New" button all render. A second case without `action` — assert it still renders the title/description without throwing.

- [ ] **Step 5: Run and verify pass**

Run: `npm test -- not-found-page error-page loading-page empty-state` (from the rendered project directory)
Expected: PASS, all four files.

- [ ] **Step 6: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/pages/static/not-found-page.test.tsx frontend/forge_web/templates/_shared/src/pages/static/error-page.test.tsx frontend/forge_web/templates/_shared/src/pages/static/loading-page.test.tsx frontend/forge_web/templates/_shared/src/pages/static/empty-state.test.tsx
git commit -m "test(frontend): add tests for the static pages"
```

---

### Task 12: `landing-page.tsx` / `component-showcase-page.tsx` smoke tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/pages/landing/landing-page.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/pages/showcase/component-showcase-page.test.tsx`

**Interfaces:**
- Consumes: default exports `LandingPage`, `ComponentShowcasePage` — both existing, unchanged. Both need `renderWithProviders` (router, for `<Link>`s and — for the showcase page — `useForm`'s no-op form doesn't need query context, but rendering via the shared helper keeps the pattern consistent even where only the router half is strictly required).

- [ ] **Step 1: `landing-page.test.tsx`**

`renderWithProviders(<LandingPage />)`. Assert "Project structure" and "Static pages" section headings are present (structural smoke check — this page is pure static content assembled from constants, so a render-without-crashing plus a couple of anchor-text assertions is proportionate; it doesn't warrant per-`STATIC_PAGES`-entry assertions).

- [ ] **Step 2: `component-showcase-page.test.tsx`**

`renderWithProviders(<ComponentShowcasePage />)`. Assert it renders without throwing. This page assembles ~15 already-individually-tested primitives into one demo screen — the value of this test is catching a broken import/composition, not re-testing each primitive's behavior again.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- landing-page component-showcase-page` (from the rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/pages/landing/landing-page.test.tsx frontend/forge_web/templates/_shared/src/pages/showcase/component-showcase-page.test.tsx
git commit -m "test(frontend): add smoke tests for landing-page and component-showcase-page"
```

---

### Task 13: `app-shell.tsx` / `nav-sidebar.tsx` tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/components/common/app-shell.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/components/common/nav-sidebar.test.tsx`

**Interfaces:**
- Consumes: `AppShell` (prop: `children: ReactNode`), `NavSidebar` — both existing, unchanged. `nav-sidebar.tsx` is Jinja-conditional on `include_data_fetching` (the `/dashboard` nav item and its `LayoutGrid` import, per the multi-template work's bug fix) — this task's second test file directly regression-tests that.

- [ ] **Step 1: `app-shell.test.tsx`**

`renderWithProviders(<AppShell><p>Page content</p></AppShell>)`. Assert "Page content" is in the document (proves `children` renders) alongside the nav (assert "Home" — `NavSidebar`'s always-present first item — is also present, proving the shell actually composes the sidebar rather than swallowing it).

- [ ] **Step 2: `nav-sidebar.test.tsx`**

Two describe blocks or two separate render calls covering both link sets `NavSidebar` always renders (`"Home"`, `"Components"`) via `renderWithProviders(<NavSidebar />)`, plus a link-highlighting case: render at `route: "/components"`, assert the "Components" link has `aria-current="page"` (Radix/React Router's `NavLink`— actually this template's plain `NavLink` from `react-router-dom` sets `aria-current="page"` on the active link automatically) while "Home" does not. Then the regression case for the multi-template bug fix: **this file is the same for both templates** (not itself excluded), so write the assertion in terms of the `include_data_fetching` context this exact render is compiled with — i.e. write two assertions that are true in the same rendered file for whichever template it ends up in: `if (import.meta.env represents... )` — simpler: since `nav-sidebar.tsx`'s own Jinja conditional means the *rendered* file literally only contains the "Dashboard" `NavLink` JSX when `include_data_fetching` is true, just assert presence unconditionally in `base`'s test and absence unconditionally in `minimal`'s — but this is one template-source test file shared by both. Resolve this the same way the component itself resolves it: wrap the "Dashboard"-presence assertion in `{% if include_data_fetching %}`/`{% else %}` Jinja blocks in the test file too, asserting `screen.getByText("Dashboard")` exists in the `base` branch and `screen.queryByText("Dashboard")` is `null` in the `minimal` branch.

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- app-shell nav-sidebar` (from the rendered project directory, for the `base` template)
Expected: PASS, both files, with the Dashboard-present branch exercised.

Then re-render with `--template minimal` into a separate temp directory, `npm install`, and run the same command there.
Expected: PASS, with the Dashboard-absent branch exercised — this is the concrete regression check for the dead-link bug fixed during the multi-template work.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/components/common/app-shell.test.tsx frontend/forge_web/templates/_shared/src/components/common/nav-sidebar.test.tsx
git commit -m "test(frontend): add tests for app-shell and nav-sidebar, incl. the include_data_fetching regression"
```

---

### Task 14: `dashboard-page.tsx` / `item-form.tsx` tests (`base` only)

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/pages/dashboard/dashboard-page.test.tsx`
- Create: `frontend/forge_web/templates/_shared/src/pages/dashboard/item-form.test.tsx`

**Interfaces:**
- Consumes: default export `DashboardPage`, named export `ItemForm` (props: `item?: Item`, `onSuccess: () => void`) — both existing, unchanged. Both files are already excluded entirely from `minimal` by the existing manifest, so no template-conditional test-writing is needed here (unlike Task 13's `nav-sidebar.test.tsx`).
- Mocks `@/lib/hooks/use-items` wholesale (`vi.mock("@/lib/hooks/use-items", () => ({ useItems: vi.fn(), useDeleteItem: vi.fn(), useCreateItem: vi.fn(), useUpdateItem: vi.fn() }))`) — isolates these page-level tests from the hooks' real TanStack Query behavior, already covered in Task 4.

- [ ] **Step 1: `dashboard-page.test.tsx`**

With `useItems` mocked to return `{ data: undefined, isLoading: true, isError: false }` and `useDeleteItem` mocked to return `{ mutate: vi.fn() }`: `renderWithProviders(<DashboardPage />)`, assert loading skeletons render (query by `.animate-pulse`, same pattern as Task 11's loading-page test) and no table appears. With `useItems` mocked to return `{ data: [], isLoading: false, isError: false }`: assert the `EmptyState` ("No items yet") renders. With `useItems` mocked to return `{ data: [fixtureItem], isLoading: false, isError: false }` (one `Item` fixture): assert the item's `name` renders in the table, and clicking "New Item" opens the create dialog (assert "New item" dialog title appears). With `useItems` mocked to return `{ isError: true, error: new Error("boom") }`: assert `ErrorPage`'s rendering shows "boom" as the message.

- [ ] **Step 2: `item-form.test.tsx`**

With `useCreateItem`/`useUpdateItem` mocked to return `{ mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false }`: render `<ItemForm onSuccess={onSuccessSpy} />` (create mode, no `item` prop) via `renderWithProviders`. Assert the submit button reads "Create item" (proves the `item ? "Save changes" : "Create item"` branch). Type a name via `userEvent.type`, submit, `await` the assertion that `useCreateItem`'s mocked `mutateAsync` was called with `{ name: <typed value> }` and `onSuccessSpy` was called. Second case: render with an `item` fixture prop — assert the submit button reads "Save changes" and the name field is pre-filled with the fixture's name (proves `defaultValues` wiring).

- [ ] **Step 3: Run and verify pass**

Run: `npm test -- dashboard-page item-form` (from a `base`-template rendered project directory)
Expected: PASS, both files.

- [ ] **Step 4: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/pages/dashboard/dashboard-page.test.tsx frontend/forge_web/templates/_shared/src/pages/dashboard/item-form.test.tsx
git commit -m "test(frontend): add tests for dashboard-page and item-form"
```

---

### Task 15: `App.tsx` routing tests

**Files:**
- Create: `frontend/forge_web/templates/_shared/src/App.test.tsx`

**Interfaces:**
- Consumes: default export `App` — existing, unchanged. `App.tsx` is Jinja-conditional on `include_data_fetching` for the `/dashboard` route (per the multi-template work) — same shared-file-with-conditional-assertions pattern as Task 13's `nav-sidebar.test.tsx`.
- `App` constructs its own `QueryClientProvider`/`RouterProvider` internally (when `include_data_fetching` is true) — do NOT wrap it in `renderWithProviders` (that would double up the router). Use plain `render(<App />)` from `@testing-library/react`, and drive navigation by rendering fresh at each path rather than clicking through (simpler given `App`'s router is `createBrowserRouter`-based, which reads the real `window.location`, not a `MemoryRouter` — set `window.history.pushState({}, "", path)` before each render to control the starting route).

- [ ] **Step 1: Write the test file**

For each of `"/"`, `"/components"`, `"/static/not-found"`: call `window.history.pushState({}, "", path)`, `render(<App />)`, assert a piece of that route's page-specific text is present (e.g. `"/"` → landing page's "Project structure" heading; `"/components"` → showcase page renders without throwing; `"/static/not-found"` → "Page not found"). For an unmatched path (`"/totally-bogus"`), assert it also renders "Page not found" (proves the catch-all `*` route). Wrap the `/dashboard` case in `{% if include_data_fetching %}`/`{% else %}`: in the `base` branch, assert navigating to `"/dashboard"` renders the dashboard's "Items" heading (mock `@/lib/hooks/use-items` the same way as Task 14, since `DashboardPage` is real inside this render); in the `minimal` branch, assert `"/dashboard"` instead falls through to the catch-all and renders "Page not found" — a second, end-to-end confirmation of the same dead-route fix Task 13 already unit-tests at the `nav-sidebar` level.

- [ ] **Step 2: Run and verify pass**

Run: `npm test -- App.test` against a `base`-template render, then again against a `minimal`-template render (same two-render pattern as Task 13 Step 3).
Expected: PASS in both.

- [ ] **Step 3: Commit**

```bash
git add frontend/forge_web/templates/_shared/src/App.test.tsx
git commit -m "test(frontend): add routing tests for App.tsx, incl. the /dashboard minimal regression"
```

---

### Task 16: CI wiring, threshold lock-in, and empirical verification

**Files:**
- Modify: `frontend/forge_web/templates/_shared/vite.config.ts`
- Modify: `frontend/forge_web/templates/_shared/.github/workflows/ci.yml`

**Interfaces:**
- Consumes: everything from Tasks 1–15 — every source file now has a colocated test.

- [ ] **Step 1: Render `base` into a fresh temp directory and run real coverage**

```bash
forge-web new --name coverage-check --path /tmp/vitest-verify-base --api-base-url http://localhost:8080/api --template base
cd /tmp/vitest-verify-base/coverage-check
npm install
npm run test:coverage
```

Record the actual `% Lines` figure from Vitest's coverage table output.

- [ ] **Step 2: Render `minimal` into a fresh temp directory and run real coverage**

```bash
forge-web new --name coverage-check --path /tmp/vitest-verify-minimal --api-base-url http://localhost:8080/api --template minimal
cd /tmp/vitest-verify-minimal/coverage-check
npm install
npm run test:coverage
```

Record the actual `% Lines` figure.

- [ ] **Step 3: Reconcile against the 80% target**

If both renders clear 80%: proceed to Step 4 with 80% locked in, as specced. If either lands below 80%: identify the specific under-covered files from Vitest's per-file coverage table (same diagnostic approach used for the backend JaCoCo gap — read the actual missed-line output, don't guess), add targeted tests to the relevant file (as a new commit extending that file's test coverage — never amend an earlier task's commit), and re-run this step until both templates clear 80% for real. Do not lower the threshold or add coverage exclusions to paper over a genuine gap — the same discipline applied to the backend gate's 78%→93.9% closure applies here.

- [ ] **Step 4: Lock in the threshold in `vite.config.ts`**

Add to the `test.coverage` block from Task 1:

```ts
thresholds: {
  lines: 80,
},
```

- [ ] **Step 5: Add the CI coverage step**

In `frontend/forge_web/templates/_shared/.github/workflows/ci.yml`'s `build` job, after the existing `npm run build` step (or replacing it if `test:coverage` should gate before a build attempt — keep `npm run build` as its own step regardless, since it also typechecks via `tsc`), add:

```yaml
      - name: Run tests with coverage
        run: npm run test:coverage

      - name: Coverage summary
        if: always()
        run: |
          if [ -f coverage/coverage-summary.json ]; then
            {
              echo "### Code coverage (gate: 80% lines)"
              node -e "const s=require('./coverage/coverage-summary.json').total.lines; console.log('**Overall line coverage: ' + s.pct + '%** (' + s.covered + '/' + s.total + ' lines)')"
            } >> "$GITHUB_STEP_SUMMARY"
          else
            echo "### Code coverage: report not generated (tests failed before coverage was written)" >> "$GITHUB_STEP_SUMMARY"
          fi
```

This requires the `json-summary` reporter to actually produce `coverage/coverage-summary.json` — add `reporter: ["text", "html", "json-summary"]` to the `test.coverage` block in `vite.config.ts` alongside `thresholds` (v8's default reporters are `text`/`html`/`json`, which does not include `json-summary`; it must be requested explicitly).

- [ ] **Step 6: Re-verify end-to-end against the final config**

Re-run Step 1's render-and-`test:coverage` sequence one more time (fresh temp dir) against the now-final `vite.config.ts` (with `thresholds` set). Confirm the command exits 0 (threshold met) and that `coverage/coverage-summary.json` exists with a `total.lines.pct` at or above 80.

- [ ] **Step 7: Commit**

```bash
git add frontend/forge_web/templates/_shared/vite.config.ts frontend/forge_web/templates/_shared/.github/workflows/ci.yml
git commit -m "feat(frontend): gate generated project CI on 80% test coverage, add summary"
```

---

### Task 17: Documentation updates

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/CHANGELOG.md`

**Interfaces:**
- Consumes: the final, verified state from Task 16 (80% threshold locked in, CI wired, both templates confirmed passing for real) — this task documents what actually shipped, not what was planned, so write it after Task 16's Step 6 re-verification has confirmed the real numbers.

- [ ] **Step 1: Update `frontend/README.md`**

Add a bullet under "What it generates" describing the Vitest + RTL suite and the 80% coverage gate — mirroring the JaCoCo bullet already present in `backend/README.md` (added during the backend coverage-gate work): name the tooling (Vitest, React Testing Library, `@vitest/coverage-v8`), state the threshold (80% lines, aggregate) and what's excluded (`main.tsx`, type-only files), and note the two npm scripts' different roles — `npm test` (fast inner loop, no gate) vs. `npm run test:coverage` (gate enforced, what CI runs).

- [ ] **Step 2: Update `frontend/CHANGELOG.md`**

Add a bullet to the `[Unreleased]` section — mirroring the structure of the JaCoCo bullet already in `backend/CHANGELOG.md` — summarizing: the new test suite and its tooling choice (Vitest + RTL + v8, chosen over Jest to reuse the project's existing Vite transform pipeline), the 80% line-coverage gate enforced via `npm run test:coverage` (backed by `vite.config.ts`'s `test.coverage.thresholds`), the CI coverage-summary step, and the real coverage percentage both templates landed at after Task 16's verification (fill in the actual `base`/`minimal` numbers recorded there, not a placeholder).

- [ ] **Step 3: Commit**

```bash
git add frontend/README.md frontend/CHANGELOG.md
git commit -m "docs(frontend): document the generated-project coverage gate"
```
