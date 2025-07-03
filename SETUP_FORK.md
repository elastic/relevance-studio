# Setting Up Fork and Creating PR

## Step 1: Fork the Repository

1. Go to https://github.com/elastic/relevance-studio
2. Click the "Fork" button in the top right
3. Choose your GitHub account as the destination
4. Wait for the fork to complete

## Step 2: Add Your Fork as Remote

Once you have your fork, run these commands:

```bash
# Add your fork as a new remote (replace YOUR_USERNAME with your GitHub username)
git remote add fork https://github.com/YOUR_USERNAME/relevance-studio.git

# Push your feature branch to your fork
git push fork feature/serverless-mode-indicator
```

## Step 3: Create Pull Request

1. Go to your fork on GitHub: https://github.com/YOUR_USERNAME/relevance-studio
2. You should see a banner suggesting to create a PR for the `feature/serverless-mode-indicator` branch
3. Click "Compare & pull request"
4. Use the content from `PR_DESCRIPTION.md` as the PR description
5. Submit the PR

## Alternative: Using GitHub CLI

If you have GitHub CLI installed:

```bash
# Create PR directly from command line
gh pr create --title "Add serverless mode indicator to Projects page" --body-file PR_DESCRIPTION.md --repo elastic/relevance-studio
```

## Current Status

Your changes are committed locally on the `feature/serverless-mode-indicator` branch. You just need to:

1. Fork the repository
2. Add your fork as a remote
3. Push to your fork
4. Create the PR

The commit includes:
- Backend API endpoint for mode detection
- Frontend API function
- UI changes to display the serverless mode badge 