# Rariflat — Hermes Plugin Hackathon Submission Checklist

## Entry requirements

1. **Public repo** (this one)  
   https://github.com/wadezigh96/rariflat-hermes

2. **Pull request** to `NousResearch/hermes-agent`  
   Add a single file: `plugin-catalog/rariflat.yaml`  
   Use the template in this repo (`plugin-catalog/rariflat.yaml`) and replace the `sha` with the full 40-character commit SHA you want pinned.

3. **Demo video** on X  
   - Under 90 seconds  
   - Show the plugin actually working (character reactions + routing)  
   - Tag `@NousResearch`

4. **Submit both links** through the official form  
   (link is in the original Nous Research announcement post)

## Before you open the PR

- [ ] Run `hermes plugins validate ./rariflat-hermes --install-deps` (or the equivalent on your machine)
- [ ] Confirm `plugin.yaml` declares the tools and hooks you register
- [ ] Make sure the plugin loads with `hermes plugins doctor`
- [ ] Pin an exact commit SHA in the catalog YAML

## Suggested demo flow (< 90s)

1. Show the Desktop pane empty ("Waiting for tool calls…")
2. Ask Hermes to search the web → Owl awakens and reacts
3. Ask it to run a terminal command → Hephaestus forges
4. Trigger an error or a restrained action → Cerberus appears
5. Run `/rariflat` or call `rariflat_route` → show the ranking
6. End on the character that just succeeded

## What judges look for

- Usefulness (people will actually keep it enabled)
- Reliability
- Polish
- Creativity (more than a plain prompt or skill)

Rariflat scores on all four: live visual feedback + adaptive skill routing.
