import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {describe,expect,it} from 'vitest'
import AppShell from '../components/AppShell'

describe('mobile navigation',()=>{
  it('opens and closes the sidebar from the menu button',()=>{
    localStorage.removeItem('manaksathi-navigation-open')
    Object.defineProperty(window,'innerWidth',{value:390,configurable:true})
    render(<MemoryRouter><AppShell language="en" setLanguage={()=>{}}><div>Page</div></AppShell></MemoryRouter>)
    const open=screen.getByRole('button',{name:'Open navigation'})
    fireEvent.click(open)
    expect(screen.getByRole('navigation',{name:'Main navigation'}).closest('aside')).toHaveClass('open')
    fireEvent.click(screen.getAllByRole('button',{name:'Close navigation'})[0])
    expect(screen.getByRole('navigation',{name:'Main navigation'}).closest('aside')).not.toHaveClass('open')
  })

  it('collapses the visible desktop sidebar',()=>{
    localStorage.removeItem('manaksathi-navigation-open')
    Object.defineProperty(window,'innerWidth',{value:1440,configurable:true})
    const {container}=render(<MemoryRouter><AppShell language="en" setLanguage={()=>{}}><div>Page</div></AppShell></MemoryRouter>)
    expect(container.querySelector('.shell')).toHaveClass('nav-open')
    fireEvent.click(screen.getAllByRole('button',{name:'Close navigation'})[0])
    expect(container.querySelector('.shell')).toHaveClass('nav-closed')
    expect(localStorage.getItem('manaksathi-navigation-open')).toBe('false')
  })
})
