/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  EuiButton,
  EuiCode,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiPanel,
  EuiSpacer,
  EuiStepsHorizontal,
  EuiText,
  EuiTitle,
} from '@elastic/eui'
import { Page } from '../../Layout'
import FormIndices from './FormIndices'
import FormDescription from './FormDescription'
import FormJudgements from './FormJudgements'
import FormName from './FormName'
import FormParams from './FormParams'
import FormTags from './FormTags'

const WorkspacesCreate = () => {

  /**
   * Preload images to prevent flickering during transitions between steps.
   */
  const [imagesReady, setImagesReady] = useState({})
  const images = {
    preface: '/img/box.png',
    basics: '/img/sparkle.png',
    content: '/img/content.png',
    search: '/img/search.png',
    judgements: '/img/sliders.png',
  }
  useEffect(() => {
    Object.entries(images).forEach(([key, url]) => {
      const img = new Image()
      img.loading = 'eager'
      img.decoding = 'async'
      img.onload = () => setImagesReady(prev => ({ ...prev, [key]: true }))
      img.onerror = () => setImagesReady(prev => ({ ...prev, [key]: true })) // don't block on errors
      img.src = url
    })
  }, [])

  ////  State  /////////////////////////////////////////////////////////////////

  const [currentStep, setCurrentStep] = useState(0)
  const [form, setForm] = useState({
    name: '',
    description: '',
    corpus: {
      name: '',
      description: '',
      index_pattern: '*',
      indices: [],
      fields: [],
    },
    params: [
      {
        name: 'text',
        type: 'text',
        description: 'Text submitted through a search bar or prompt.',
      },
    ],
    scenarios: {
      tags: [
        {
          name: 'Head',
          color: '#16C5C0',
          description: 'Popular, broad, or ambiguous inputs. Often one or two tokens long.',
        },
        {
          name: 'Body',
          color: '#61A2FF',
          description: 'More detailed inputs. Often several tokens long.',
        },
        {
          name: 'Tail',
          color: '#EE72A6',
          description: 'Rare or highly detailed inputs. Often many tokens long.',
        },
      ]
    },
    strategies: {
      tags: [
        {
          name: 'Semantic',
          color: '#16C5C0',
          description: 'Queries that use dense or sparse vectors (e.g. ELSER).',
        },
        {
          name: 'Lexical',
          color: '#61A2FF',
          description: 'Queries that use the inverted index (e.g. BM25).',
        },
        {
          name: 'Hybrid',
          color: '#EE72A6',
          description: 'Queries that combine different search methods (e.g. RRF).',
        },
        {
          name: 'Reranking',
          color: '#EAAE01',
          description: 'Queries that use rerankers.',
        },
      ]
    },
    judgements: {
      max: 4,
      min: 0,
      description: `#### Rubric

**\`4\`** → Completely relevant.
**\`3\`** → Mostly relevant despite minor flaws.
**\`2\`** → Somewhat relevant but with obvious flaws.
**\`1\`** → Mostly irrelevant despite minor relevant details.
**\`0\`** → Completely irrelevant.`
    }
  })
  const [stepsVisited, setStepsVisited] = useState({})

  ////  Steps  /////////////////////////////////////////////////////////////////

  const steps = [
    {
      id: 'preface',
      section: 'preface',
      title: "Let's get started!",
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            We'll prepare a space in which humans and agents can work toward a common goal.
          </p>
          <EuiSpacer />
          <p>
            <AnimatePresence mode='wait'>
              <motion.img
                alt='Preface'
                animate={{ opacity: imagesReady.preface ? 1 : 0 }} // fade in when ready
                decoding='async'
                height={100} // reserve space to prevent layout shift
                initial={{ opacity: 0 }} // starts invisible
                key='image-preface'
                loading='eager'
                src={images.preface}
                style={{ display: 'block', margin: '0 auto' }}
                transition={{ duration: 0.3, ease: 'ease-out' }}
              />
            </AnimatePresence>
          </p>
        </div>
      ),
      validate: () => true,
    },
    {
      id: 'transition-basics',
      section: 'basics',
      title: 'Part 1. The Basics',
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            Let's start with the name and purpose of this workspace.<br />
            This will set the direction for everything else.
          </p>
          <EuiSpacer />
          <p>
            <AnimatePresence mode='wait'>
              <motion.img
                alt='Basics'
                animate={{ opacity: imagesReady.basics ? 1 : 0 }} // fade in when ready
                decoding='async'
                height={100} // reserve space to prevent layout shift
                initial={{ opacity: 0 }} // starts invisible
                key='image-basics'
                loading='eager'
                src={images.basics}
                style={{ display: 'block', margin: '0 auto' }}
                transition={{ duration: 0.3, ease: 'ease-out' }}
              />
            </AnimatePresence>
          </p>
        </div>
      ),
      validate: () => true,
    },
    {
      id: 'name',
      section: 'basics',
      title: 'Give your workspace a name.',
      description: (
        <>
          Make it fit the purpose of the workspace.
        </>
      ),
      changeable: true,
      render: (form) => (
        <FormName
          onChange={(e) => {
            setForm(prev => ({ ...prev, name: e.target.value }))
          }}
          value={form.name}
        />
      ),
      validate: (form) => !!form.name?.trim(),
    },
    {
      id: 'description',
      section: 'basics',
      title: 'Describe its purpose.',
      description: (
        <>
          What outcomes are you working toward?
        </>
      ),
      changeable: true,
      render: (form) => (
        <FormDescription
          onChange={(value) => {
            setForm(prev => ({ ...prev, description: value }))
          }}
          value={form.description}
        />
      ),
      validate: (form) => !!form.description?.trim(),
    },
    {
      id: 'transition-content',
      section: 'content',
      title: 'Part 2. The Content',
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            Let's connect the data that powers your search experience.
          </p>
          <EuiSpacer />
          <p>
            <AnimatePresence mode='wait'>
              <motion.img
                alt='Content'
                animate={{ opacity: imagesReady.content ? 1 : 0 }} // fade in when ready
                decoding='async'
                height={100} // reserve space to prevent layout shift
                initial={{ opacity: 0 }} // starts invisible
                key='image-content'
                loading='eager'
                src={images.content}
                style={{ display: 'block', margin: '0 auto' }}
                transition={{ duration: 0.3, ease: 'ease-out' }}
              />
            </AnimatePresence>
          </p>
        </div>
      ),
      validate: () => true,
    },
    {
      id: 'content', // corpus
      section: 'content',
      title: 'Scope the indices.',
      description: (
        <>
          Specify the index pattern in which your content resides.<br />
          <EuiSpacer size='xs' />
          <EuiText color='subdued' size='xs'>
            This will be the target for all searches in the workspace.
          </EuiText>
        </>
      ),
      render: (form) => (
        <FormIndices
          index_pattern={form.corpus.index_pattern}
          onChangeIndexPattern={(e) => {
            setForm(prev => ({
              ...prev, corpus: { ...prev.corpus, index_pattern: e.target.value }
            }))
          }}
        />
      ),
      validate: (form) => !!form.corpus.index_pattern?.trim(),
    },
    {
      id: 'display',
      section: 'content',
      title: 'Create a view for your documents.',
      description: (
        <>
          This makes it easier to judge relevance. And it makes searches more efficient.
        </>
      ),
      changeable: true,
      validate: () => true,
    },
    {
      id: 'transition-search',
      section: 'search',
      title: 'Part 3. The Search Criteria',
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            Let's define the inputs and categories of your scenarios and strategies.
          </p>
          <EuiSpacer />
          <p>
            <AnimatePresence mode='wait'>
              <motion.img
                alt='Search'
                animate={{ opacity: imagesReady.search ? 1 : 0 }} // fade in when ready
                decoding='async'
                height={100} // reserve space to prevent layout shift
                initial={{ opacity: 0 }} // starts invisible
                key='image-search'
                loading='eager'
                src={images.search}
                style={{ display: 'block', margin: '0 auto' }}
                transition={{ duration: 0.3, ease: 'ease-out' }}
              />
            </AnimatePresence>
          </p>
        </div>
      ),
      validate: () => true,
    },
    {
      id: 'params',
      section: 'search',
      title: 'Define the inputs of your search interface.',
      description: (
        <>
          These will be the parameters accepted by your scenarios and strategies.
          <EuiSpacer size='xs' />
          <EuiText color='subdued' size='xs'>
            We recommend having at least a <EuiCode>text</EuiCode> parameter representing the submission of a search bar or prompt.
          </EuiText>
        </>
      ),
      changeable: true,
      render: (form) => (
        <FormParams params={form.params} />
      ),
      validate: () => true,
    },
    {
      id: 'scenarios',
      section: 'search',
      title: 'Categorize your scenarios.',
      description: (
        <>
          These tags let you segment your analysis of relevance by different query intents.
        </>
      ),
      changeable: true,
      render: (form) => (
        <FormTags tags={form.scenarios.tags} />
      ),
      validate: () => true,
    },
    {
      id: 'strategies',
      section: 'search',
      title: 'Categorize your strategies.',
      description: (
        <>
          These tags let you segment your analysis of relevance by different strategies.
        </>
      ),
      changeable: true,
      render: (form) => (
        <FormTags tags={form.strategies.tags} />
      ),
      validate: () => true,
    },
    {
      id: 'transition-judgements',
      section: 'judgements',
      title: 'Part 4. Judging Relevance',
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            Lastly, we'll define how humans and agents should judge relevance.
          </p>
          <EuiSpacer />
          <p>
            <AnimatePresence mode='wait'>
              <motion.img
                alt='Judgements'
                animate={{ opacity: imagesReady.judgements ? 1 : 0 }} // fade in when ready
                decoding='async'
                height={100} // reserve space to prevent layout shift
                initial={{ opacity: 0 }} // starts invisible
                key='image-judgements'
                loading='eager'
                src={images.judgements}
                style={{ display: 'block', margin: '0 auto' }}
                transition={{ duration: 0.3, ease: 'ease-out' }}
              />
            </AnimatePresence>
          </p>
        </div>
      ),
      validate: () => true,
    },
    {
      id: 'judgements',
      section: 'judgements',
      title: 'Define the rating scale.',
      description: (
        <>
          Explain how to judge the relevance of content for search scenarios.<br />
          <EuiSpacer size='xs' />
          <EuiText color='subdued' size='xs'>
            We recommend using the default scale and tailoring the rubric to your use case.
          </EuiText>
        </>
      ),
      changeable: false,
      render: (form) => (
        <FormJudgements
          description={form.judgements.description}
          max={form.judgements.max}
          min={form.judgements.min}
          onChangeMax={(value) => {
            setForm(prev => ({
              ...prev, judgements: { ...prev.judgements, max: value }
            }))
          }}
          onChangeMin={(value) => {
            setForm(prev => ({
              ...prev, judgements: { ...prev.judgements, min: value }
            }))
          }}
          onChangeDescription={(value) => {
            setForm(prev => ({
              ...prev, judgements: { ...prev.judgements, description: value }
            }))
          }}
        />
      ),
      validate: (form) => !!form.judgements.description?.trim(),
    },
    {
      id: 'transition-review',
      section: 'review',
      title: 'Review',
      description: '',
      render: (form) => (
        <div style={{ textAlign: 'center' }}>
          <p>
            Everything look good?
          </p>
        </div>
      ),
      validate: () => true,
    },
  ]

  ////  Navigation  ////////////////////////////////////////////////////////////

  const animations = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
    exit: { opacity: 0, y: -10, transition: { duration: 0.3, ease: 'easeIn' } },
  }

  const scrollRef = useRef(null)

  const scrollToTop = () => scrollRef.current?.scroll({ top: 0, behavior: 'smooth' })

  /**
   * When navigating to a step, mark the step as visited and then scroll to the
   * top of the page.
   */
  useEffect(() => {
    setStepsVisited(prev => ({ ...prev, [currentStep]: true }))
    scrollToTop()
  }, [currentStep])

  /**
   * Go to the previous step.
   */
  const onClickBack = () => {
    setCurrentStep(currentStep - 1)
  }

  /**
   * Go to the next step.
   */
  const onClickNext = (e) => {
    if (e) e.preventDefault(); // prevent browser's form submission behavior

    // parseInt safety, because js concatenates "2" + 1 as "21" like a child...
    setCurrentStep(parseInt(currentStep) + 1)
  }

  /**
   * Navigate to the first page of a section, but only if that section has been
   * visited already to avoid skipping ahead and missing prerequisites.
   */
  const onClickSection = (section) => {
    for (const i in steps) {
      if (steps[i].section == section && stepsVisited[i])
        return setCurrentStep(i)
    }
  }

  /**
   * Section buttons can be clicked if the first page of the section has been
   * visited before.
   */
  const isSectionNavigable = (section) => {
    for (const i in steps) {
      if (steps[i].section == section && stepsVisited[i])
        return true
    }
  }

  /**
   * Section is complete if all steps have been visited and have valid inputs.
   */
  const sectionStatus = (section) => {
    for (const i in steps) {
      if (steps[i].section !== section)
        continue
      if (!stepsVisited[i] || !steps[i].validate(form))
        return 'incomplete'
    }
    return 'complete'
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderNavigation = () => (
    <div style={{ margin: '0 auto', width: '400px' }}>
      <EuiSpacer size='l' />
      <EuiFlexGroup justifyContent='center' responsive={false}>
        {currentStep == 0 &&
          <EuiFlexItem>
            <EuiButton
              fill
              onClick={onClickNext}
              size='s'
              type='submit'
            >
              Begin
            </EuiButton>
          </EuiFlexItem>
        }
        {currentStep > 0 &&
          <>
            <EuiFlexItem>
              <EuiButton color='text' onClick={onClickBack} size='s'>
                Back
              </EuiButton>
            </EuiFlexItem>
            <EuiFlexItem>
              <EuiButton
                disabled={steps[currentStep].validate ? !steps[currentStep].validate(form) : false}
                fill
                onClick={onClickNext}
                size='s'
                type='submit'
              >
                Next
              </EuiButton>
            </EuiFlexItem>
          </>
        }
      </EuiFlexGroup>
      <EuiSpacer size='l' />
    </div>
  )

  return (
    <Page panelled mainRef={scrollRef}>
      <EuiPanel color='transparent'>

        {/* Page title */}
        <EuiSpacer />
        <EuiTitle
          size={currentStep === 0 ? 'l' : 'xs'}
          style={{
            fontWeight: currentStep === 0 ? 700 : 500,
            textAlign: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          <h1>
            <big>
              Create Workspace
            </big>
          </h1>
        </EuiTitle>

        {/* Progress bar */}
        <div style={{ margin: '0 auto', width: '600px' }}>
          <EuiStepsHorizontal
            size={currentStep === 0 ? 'm' : 'xs'}
            steps={[
              {
                disabled: !isSectionNavigable('basics'),
                onClick: () => steps[currentStep].section == 'preface' ? '' : onClickSection('basics'),
                status: steps[currentStep].section === 'basics' ? 'current' : sectionStatus('basics'),
                title: (
                  <EuiText size={currentStep === 0 ? 's' : 'xs'} style={{ fontWeight: isSectionNavigable('basics') ? 600 : 400 }}>
                    Basics
                  </EuiText>
                ),
              },
              {
                disabled: !isSectionNavigable('content'),
                onClick: () => steps[currentStep].section == 'preface' ? '' : onClickSection('content'),
                status: steps[currentStep].section === 'content' ? 'current' : sectionStatus('content'),
                title: (
                  <EuiText size={currentStep === 0 ? 's' : 'xs'} style={{ fontWeight: isSectionNavigable('content') ? 600 : 400 }}>
                    Content
                  </EuiText>
                ),
              },
              {
                disabled: !isSectionNavigable('search'),
                onClick: () => steps[currentStep].section == 'preface' ? '' : onClickSection('search'),
                status: steps[currentStep].section === 'search' ? 'current' : sectionStatus('search'),
                title: (
                  <EuiText size={currentStep === 0 ? 's' : 'xs'} style={{ fontWeight: isSectionNavigable('search') ? 600 : 400 }}>
                    Search
                  </EuiText>
                ),
              },
              {
                disabled: !isSectionNavigable('judgements'),
                onClick: () => steps[currentStep].section == 'preface' ? '' : onClickSection('judgements'),
                status: steps[currentStep].section === 'judgements' ? 'current' : sectionStatus('judgements'),
                title: (
                  <EuiText size={currentStep === 0 ? 's' : 'xs'} style={{ fontWeight: isSectionNavigable('judgements') ? 600 : 400 }}>
                    Judge
                  </EuiText>
                ),
              },
              {
                disabled: !isSectionNavigable('review'),
                onClick: () => steps[currentStep].section == 'preface' ? '' : onClickSection('review'),
                status: steps[currentStep].section === 'review' ? 'current' : sectionStatus('review'),
                title: (
                  <EuiText size={currentStep === 0 ? 's' : 'xs'} style={{ fontWeight: isSectionNavigable('review') ? 600 : 400 }}>
                    Review
                  </EuiText>
                ),
              }
            ]}
            style={{
              margin: '0 auto',
              transition: 'all 0.3s ease',
              width: currentStep === 0 ? '600px' : '400px'
            }}
          />
        </div>
        <EuiSpacer size='xxl' />

        {/* Step title */}
        <AnimatePresence mode='wait'>
          <motion.div
            key={currentStep}
            variants={animations}
            initial='initial'
            animate='animate'
            exit='exit'
          >

            {!!steps[currentStep].title &&
              <>
                <EuiSpacer />
                <EuiTitle style={{ textAlign: 'center' }}>
                  <h2 style={{ fontWeight: 700 }}>
                    <big>
                      {steps[currentStep].title}
                    </big>
                  </h2>
                </EuiTitle>
                <EuiSpacer />
              </>
            }

            {/* Step description */}
            {!!steps[currentStep].description &&
              <>
                <EuiText style={{ textAlign: 'center' }}>
                  {steps[currentStep].description}
                </EuiText>
                <EuiSpacer size='xl' />
              </>
            }
            {/*
        {!!steps[currentStep].changeable &&
          <div style={{ textAlign: 'center' }}>
            <EuiBadge size='s'>
              <EuiText color='subdued' size='xs'>
                <small>You can change this later.</small>
              </EuiText>
            </EuiBadge>
            <EuiSpacer size='m' />
          </div>
        }
        */}
          </motion.div>
        </AnimatePresence>

        {/* Form */}
        <EuiForm component='form' fullWidth onSubmit={onClickNext}>

          {/* Content */}
          <AnimatePresence mode='wait'>
            <motion.div
              key={currentStep}
              variants={animations}
              initial='initial'
              animate='animate'
              exit='exit'
            >
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                {!!steps[currentStep].render &&
                  steps[currentStep].render(form)
                }
              </div>
            </motion.div>
          </AnimatePresence>

          <EuiSpacer size='xl' />

          {/* Navigation */}
          {renderNavigation()}
        </EuiForm>
      </EuiPanel>
    </Page>
  )
}

export default WorkspacesCreate