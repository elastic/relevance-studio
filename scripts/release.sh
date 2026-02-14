#!/usr/bin/env bash
# 
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.
#
# Elasticsearch Relevance Studio - Release Script
#
# Usage:
#   ./scripts/release.sh VERSION
#   ./scripts/release.sh 1.0.0
#
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

VERSION=""

# =============================================================================
# Colors and Formatting
# =============================================================================

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  BOLD='\033[1m'
  DIM='\033[2m'
  RED='\033[0;31m'
  PINK='\033[0;35m'
  GREEN='\033[0;32m'
  YELLOW='\033[0;33m'
  BLUE='\033[0;34m'
  CYAN='\033[0;36m'
  ITALIC='\033[3m'
  RESET='\033[0m'
else
  BOLD='' DIM='' PINK='' RED='' GREEN='' YELLOW='' BLUE='' CYAN='' ITALIC='' RESET=''
fi

# =============================================================================
# Output Helpers
# =============================================================================

print_step() {
  echo -e "${BOLD}$1${RESET}"
}

print_info() {
  echo -e "  $1"
}

print_success() {
  echo -e "  ${GREEN}✓${RESET} $1"
}

print_warning() {
  echo -e "  ${YELLOW}!${RESET} $1"
}

print_error() {
  echo -e "  ${RED}✗${RESET} $1" >&2
}

print_divider() {
  echo -e "  ${DIM}────────────────────────────────────────────────────────────────────────────────${RESET}"
}

# =============================================================================
# Utility Functions
# =============================================================================

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Get the latest semantic version tag from git
get_latest_version() {
  git tag -l 'v*' 2>/dev/null | \
    { grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true; } | \
    sort -t. -k1,1nr -k2,2nr -k3,3nr | \
    head -n1
}

# =============================================================================
# Argument Parsing
# =============================================================================

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        if [[ -z "$VERSION" ]]; then
          VERSION="$1"
        else
          print_error "Unknown argument: $1"
          print_usage
          exit 1
        fi
        shift
        ;;
    esac
  done
}

print_usage() {
  echo ""
  echo -e "${BOLD}Usage:${RESET}"
  echo "  release.sh VERSION"
  echo "  release.sh [options]"
  echo ""
  echo -e "${BOLD}Arguments:${RESET}"
  echo -e "  VERSION                   ${DIM}# Semantic version number (e.g., 1.0.0 or v1.0.0)${RESET}"
  echo -e "                            ${DIM}# Format: [v]{major}.{minor}.{patch}${RESET}"
  echo ""
  echo -e "${BOLD}Options:${RESET}"
  echo -e "  -h, --help                ${DIM}# Show this help message${RESET}"
  echo ""
  echo -e "${BOLD}Examples:${RESET}"
  echo -e "  release.sh 1.0.0          ${DIM}# First release${RESET}"
  echo -e "  release.sh v1.0.1         ${DIM}# Patch release (v prefix is optional)${RESET}"
  echo -e "  release.sh 1.1.0          ${DIM}# Minor release (requires docs/docs/v1.1/)${RESET}"
  echo -e "  release.sh v2.0.0         ${DIM}# Major release (requires docs/docs/v2.0/)${RESET}"
  echo ""
  print_divider
  echo ""
  echo -e "${BOLD}What this release script does:${RESET}"
  echo ""
  echo -e "  1. Validates prerequisites:"
  echo -e "     - Must be on main branch"
  echo -e "     - No modified or staged tracked files"
  echo -e "     - Tag v{version} must not already exist"
  echo -e "     - Local branch release/v{version} must not exist"
  echo -e "     - Remote branch release/v{version} must not exist"
  echo ""
  echo -e "  2. Checks documentation versions (only for new minor/major releases):"
  echo -e "     - Ensures docs/docs/v{major}.{minor}/ exists"
  echo ""
  echo -e "  3. Creates the release branch:"
  echo -e "     - git checkout -b release/v{version}"
  echo ""
  echo -e "  4. Updates version number implementations:"
  echo -e "     - Updates package.json version field"
  echo ""
  echo -e "  5. Commits and tags:"
  echo -e "     - git commit -m \"Release v{version}\""
  echo -e "     - git tag -a v{version} -m \"Release v{version}\""
  echo ""
  echo -e "  6. Displays next steps for publishing the release (branch/tag push instructions)"
  echo ""
  echo -e "  ${DIM}After you push the tag, the release.yml workflow automatically:${RESET}"
  echo -e "  ${DIM}- Runs unit tests${RESET}"
  echo -e "  ${DIM}- Creates GitHub release (if tests pass)${RESET}"
  echo ""
}

# =============================================================================
# Validation
# =============================================================================

validate_version() {
  if [[ -z "$VERSION" ]]; then
    print_usage
    exit 1
  fi
  
  # Strip 'v' prefix if present
  VERSION="${VERSION#v}"
  
  # Validate semver format
  if [[ ! "$VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo ""
    print_error "Invalid version format: $VERSION"
    echo ""
    print_info "Expected: {major}.{minor}.{patch} (e.g., 1.0.0 or v1.0.0)"
    echo ""
    exit 1
  fi
  
  # Extract version components
  VERSION_MAJOR="${BASH_REMATCH[1]}"
  VERSION_MINOR="${BASH_REMATCH[2]}"
  VERSION_PATCH="${BASH_REMATCH[3]}"
}

check_prerequisites() {
  print_step "Checking prerequisites..."
  
  local errors=false
  
  # Check git
  if command_exists git; then
    print_success "git"
  else
    print_error "git - not found"
    errors=true
  fi
  
  # Check we're in a git repo
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    print_error "Not in a git repository"
    errors=true
  fi
  
  # Check we're on main
  local current_branch
  current_branch=$(git branch --show-current)
  if [[ "$current_branch" != "main" ]]; then
    print_error "Must be on main branch (currently on: $current_branch)"
    errors=true
  else
    print_success "On main branch"
  fi
  
  # Check for modified/staged tracked files (ignore untracked)
  if git status --porcelain | grep -q '^[MADR]'; then
    print_error "Modified or staged files detected"
    git status --short | grep '^[MADR]' | sed 's/^/    /'
    errors=true
  else
    print_success "No modified or staged files"
  fi
  
  # Check if tag already exists
  if git rev-parse "$TAG" >/dev/null 2>&1; then
    print_error "Tag $TAG already exists"
    errors=true
  else
    print_success "Tag $TAG available"
  fi
  
  # Check if local branch already exists
  if git rev-parse --verify "$RELEASE_BRANCH" >/dev/null 2>&1; then
    print_error "Local branch $RELEASE_BRANCH already exists"
    errors=true
  else
    print_success "Local branch $RELEASE_BRANCH available"
  fi
  
  # Check if remote branch already exists
  if git ls-remote --exit-code --heads origin "$RELEASE_BRANCH" >/dev/null 2>&1; then
    print_error "Remote branch $RELEASE_BRANCH already exists on origin"
    errors=true
  else
    print_success "Remote branch $RELEASE_BRANCH available"
  fi
  
  if [[ "$errors" == true ]]; then
    echo ""
    print_error "Prerequisites check failed"
    exit 1
  fi
  
  echo ""
}

# =============================================================================
# Version Docs Check
# =============================================================================

check_version_docs() {
  local latest_tag
  latest_tag=$(get_latest_version)
  
  if [[ -n "$latest_tag" ]]; then
    # Extract major.minor from latest tag
    if [[ "$latest_tag" =~ ^v([0-9]+)\.([0-9]+)\. ]]; then
      local latest_major="${BASH_REMATCH[1]}"
      local latest_minor="${BASH_REMATCH[2]}"
      
      # Check if this is a new minor version (different major.minor)
      if [[ "$VERSION_MAJOR.$VERSION_MINOR" != "$latest_major.$latest_minor" ]]; then
        print_step "Checking version documentation..."
        
        print_info "New minor version: ${latest_major}.${latest_minor} → ${VERSION_MAJOR}.${VERSION_MINOR}"
        
        local docs_dir="docs/docs/v${VERSION_MAJOR}.${VERSION_MINOR}"
        
        if [[ ! -d "$docs_dir" ]]; then
          echo ""
          print_error "Documentation directory not found: $docs_dir"
          echo ""
          print_info "Before releasing a new minor version, you must:"
          print_info "  ${DIM}1. Create the versioned docs directory:${RESET}"
          print_info "     ${DIM}mkdir -p $docs_dir${RESET}"
          print_info "  ${DIM}2. Copy or create documentation for this version${RESET}"
          print_info "  ${DIM}3. Update docs/index.html to include v${VERSION_MAJOR}.${VERSION_MINOR}${RESET}"
          echo ""
          exit 1
        fi
        
        print_success "Found versioned docs: $docs_dir"
        echo ""
      fi
    fi
  else
    # This is the first release
    print_step "Checking version documentation..."
    
    print_info "First release: v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}"
    
    local docs_dir="docs/docs/v${VERSION_MAJOR}.${VERSION_MINOR}"
    
    if [[ ! -d "$docs_dir" ]]; then
      echo ""
      print_error "Documentation directory not found: $docs_dir"
      echo ""
      print_info "Before the first release, you must:"
      print_info "  ${DIM}1. Create the versioned docs directory:${RESET}"
      print_info "     ${DIM}mkdir -p $docs_dir${RESET}"
      print_info "  ${DIM}2. Add documentation for this version${RESET}"
      print_info "  ${DIM}3. Update docs/index.html to include v${VERSION_MAJOR}.${VERSION_MINOR}${RESET}"
      echo ""
      exit 1
    fi
    
    print_success "Found versioned docs: $docs_dir"
    echo ""
  fi
}

# =============================================================================
# Version Updates
# =============================================================================

update_package_json() {
  echo ""
  print_step "Updating version numbers..."
  
  local package_json="package.json"
  
  if [[ ! -f "$package_json" ]]; then
    print_error "package.json not found"
    exit 1
  fi
  
  # Update package.json with platform-specific sed
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires backup extension
    sed -i '' "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" "$package_json"
  else
    # Linux sed
    sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" "$package_json"
  fi
  
  print_success "package.json"
  
  # TODO: Add version to UI
  # Examples:
  # - Create src/ui/js/version.js with exported VERSION constant
  # - Update webpack config to inject VERSION via DefinePlugin
  # - Update .env-production with VERSION variable
  
  echo ""
}

# =============================================================================
# Release Creation
# =============================================================================

create_release() {
  print_step "Creating release..."
  
  # Create release branch
  print_info "Creating branch: $RELEASE_BRANCH"
  git checkout -b "$RELEASE_BRANCH" >/dev/null 2>&1
  print_success "Branch created"
  
  # Update versions
  update_package_json
  
  # Commit
  print_step "Committing changes..."
  git add -A
  git commit -m "Release ${TAG}" >/dev/null 2>&1
  print_success "Changes committed"
  
  # Tag
  echo ""
  print_step "Creating tag: $TAG"
  git tag -a "$TAG" -m "Release ${TAG}"
  print_success "Tag created"
  
  echo ""
}

# =============================================================================
# Completion
# =============================================================================

print_completion() {
  print_step "Release prepared successfully!"
  print_divider
  echo ""
  print_info "${BOLD}Branch:${RESET} $RELEASE_BRANCH"
  print_info "${BOLD}Tag:${RESET}    $TAG"
  echo ""
  print_step "Next steps:"
  echo ""
  print_info "1. Review the changes:"
  echo ""
  print_info "     ${BOLD}git show${RESET}"
  echo ""
  print_info "2. Push the branch and tag:"
  echo ""
  print_info "     ${BOLD}git push -u origin $RELEASE_BRANCH && git push origin $TAG${RESET}"
  echo ""
  print_info "3.  GitHub Actions will run tests and create a release upon passing."
  echo ""
  print_info "     ${BOLD}Monitor: https://github.com/elastic/relevance-studio/actions${RESET}"
  echo ""
  print_info "4. Return to the main branch for continued development:"
  echo ""
  print_info "     ${BOLD}git checkout main${RESET}"
  echo ""
  print_divider
  print_info "To undo (before pushing):"
  echo ""
  print_info "  git checkout main && git branch -D $RELEASE_BRANCH && git tag -d $TAG"
  echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
  # Parse arguments
  parse_args "$@"
  
  # Validate version format
  validate_version
  
  # Set release identifiers
  RELEASE_BRANCH="release/v${VERSION}"
  TAG="v${VERSION}"
  
  echo ""
  print_step "Creating release ${TAG}"
  echo ""
  
  # Run checks
  check_prerequisites
  check_version_docs
  
  # Create the release
  create_release
  
  # Show completion message
  print_completion
}

main "$@"
