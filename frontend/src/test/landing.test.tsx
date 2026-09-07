import {render,screen} from '@testing-library/react';import {MemoryRouter} from 'react-router-dom';import {describe,expect,it,vi} from 'vitest';import Landing from '../pages/Landing'
describe('Landing',()=>{it('shows the three primary actions',()=>{render(<MemoryRouter><Landing language="en" audience="industry" setAudience={vi.fn()}/></MemoryRouter>);expect(screen.getByText('Ask the assistant')).toBeInTheDocument();expect(screen.getByText('Find a standard')).toBeInTheDocument();expect(screen.getByText('Verify certification')).toBeInTheDocument()})})

