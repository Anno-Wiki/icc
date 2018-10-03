insert into book (title, sort_title, url, author_id, published, added, summary) values 

('Heart of Darkness', 'Heart of Darkness', 'heart_of_darkness',
    (select id from author where url='joseph_conrad'), '1899-00-00', NOW(),
'Heart of Darkness (1899) is a novella by Polish-English novelist Joseph Conrad
about a voyage up the Congo River into the Congo Free State in the heart of
Africa. Charles Marlow, the narrator, tells his story to friends aboard a boat
anchored on the River Thames. This setting provides the frame for Marlow’s
story of his obsession with the ivory trader Kurtz, which enables Conrad to
create a parallel between what Conrad calls “the greatest town on earth”,
London, and Africa as places of darkness.

Central to Conrad’s work is the idea that there is little difference between
so-called civilised people and those described as savages; Heart of Darkness
raises questions about imperialism and racism.

Originally issued as a three-part serial story in Blackwood’s Magazine to
celebrate the thousandth edition of the magazine, Heart of Darkness has been
widely re-published and translated into many languages. In 1998, the Modern
Library ranked Heart of Darkness 67th on their list of the 100 best novels in
English of the twentieth century.'), 

('War and Peace', 'War and Peace', 'war_and_peace', 
    (select id from author where url='leo_tolstoy'), '1869-00-00', NOW(),
'War and Peace is a novel by the Russian author Leo Tolstoy. It is regarded as a
central work of world literature and one of Tolstoy’s finest literary
achievements.

The novel chronicles the history of the French invasion of Russia and the
impact of the Napoleonic era on Tsarist society through the stories of five
Russian aristocratic families. Portions of an earlier version, titled The Year
1805, were serialized in The Russian Messenger from 1865 to 1867. The novel was
first published in its entirety in 1869.

Tolstoy said War and Peace is “not a novel, even less is it a poem, and still
less a historical chronicle”. Large sections, especially the later chapters,
are a philosophical discussion rather than narrative. Tolstoy also said that
the best Russian literature does not conform to standards and hence hesitated
to call War and Peace a novel. Instead, he regarded Anna Karenina as his first
true novel. The Encyclopædia Britannica states: “It can be argued that no
single English novel attains the universality of the Russian writer Leo
Tolstoy’s War and Peace”.');
