// Force-included (g++ -include) when building the 2013 search program with a C++11-or-later
// compiler. No original source file is edited.
//
// Why it is needed: the 2013 sources say `using namespace boost;` at global scope and
// `namespace NEAT { using namespace std; }`, and then write `shared_ptr` unqualified. In 2013 only
// Boost had that name. Since C++11 the standard library has it too, so the unqualified name is
// ambiguous and the code no longer compiles. (An older C++ standard is not an option: the Boost
// that current Ubuntu ships needs C++11 or later.)
//
// What it does: says, inside the program's own namespaces, that the Boost names are meant, which
// is what the code always meant. A using-declaration inside a namespace is found before the names
// that using-directives make visible from outside it, so the ambiguity disappears. Behaviour is
// unchanged: the same Boost smart pointers are used as in 2013.
#ifndef COMPAT_2013_SEARCH_H
#define COMPAT_2013_SEARCH_H
#ifdef __cplusplus

// NEAT_GeneticIndividual.cpp has `#include <iomanip>` in the middle of namespace NEAT. With the
// 2013 standard library that header had already been pulled in by then, so the line did nothing;
// today it would declare the library inside NEAT::std. Including it here restores the 2013
// situation (the later line is skipped by the header's own include guard).
#include <iomanip>
#include <iostream>
#include <sstream>
#include <fstream>
#include <ctime>

#include <boost/shared_ptr.hpp>
#include <boost/weak_ptr.hpp>
#include <boost/pointer_cast.hpp>

// shared_ptr and its casts: Boost-only in 2013, also in the standard library today.
#define COMPAT_2013_BOOST_NAMES            \
    using boost::shared_ptr;               \
    using boost::weak_ptr;                 \
    using boost::static_pointer_cast;      \
    using boost::dynamic_pointer_cast;     \
    using boost::const_pointer_cast;

namespace NEAT  { COMPAT_2013_BOOST_NAMES }
namespace HCUBE { COMPAT_2013_BOOST_NAMES }

// The threading names (mutex, thread, bind), likewise. Only for the Hypercube_NEAT part of the
// program, whose sources include Boost.Thread themselves (its build defines NOPCH; the NEAT
// library's does not). Pulling Boost.Thread into the NEAT library's files as well would make
// their plain system("PAUSE") calls ambiguous with the namespace boost::system.
#ifdef NOPCH
#include <boost/thread.hpp>
#include <boost/bind.hpp>
namespace HCUBE {
    using boost::mutex;
    using boost::thread;
    using boost::bind;
}
#endif

#endif  // __cplusplus
#endif  // COMPAT_2013_SEARCH_H
