import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BookCover from './BookCover.vue'

describe('BookCover.vue', () => {
  it('renders the image when a cover URL is given', () => {
    const wrapper = mount(BookCover, { props: { src: '/media/covers/a.jpg', title: 'Dune' } })
    expect(wrapper.find('img').attributes('src')).toBe('/media/covers/a.jpg')
  })

  it('renders a generated cover when there is no image', () => {
    const wrapper = mount(BookCover, { props: { title: 'Dune', author: 'Frank Herbert' } })
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('Frank Herbert')
  })

  it('falls back to a generated cover when the image fails to load', async () => {
    const wrapper = mount(BookCover, { props: { src: '/broken.jpg', title: 'Dune' } })
    await wrapper.find('img').trigger('error')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('[role="img"]').attributes('aria-label')).toBe('Dune cover')
  })
})
